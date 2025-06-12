import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
import numpy as np
import threading
import time
import os
from datetime import timedelta
import subprocess
from PIL import Image, ImageTk
import json

class ThumbnailEditor:
    def __init__(self, parent, video_path, video_info, point_entries):
        self.parent = parent
        self.video_path = video_path
        self.video_info = video_info
        self.point_entries = point_entries
        
        self.window = tk.Toplevel(parent)
        self.window.title("台形補正設定")
        self.window.geometry("800x700")
        self.window.grab_set()  # モーダルウィンドウにする
        
        self.current_frame = None
        self.display_frame = None
        self.canvas = None
        self.points = []
        self.dragging_point = None
        self.scale_factor = 1.0
        
        self.setup_ui()
        self.load_initial_frame()
    
    def setup_ui(self):
        # 時間選択フレーム
        time_frame = tk.Frame(self.window)
        time_frame.pack(pady=10, fill='x', padx=10)
        
        tk.Label(time_frame, text="プレビューする時間:").pack(side='left')
        self.preview_h = tk.Spinbox(time_frame, from_=0, to=23, width=3, format="%02.0f")
        self.preview_h.pack(side='left', padx=2)
        tk.Label(time_frame, text="時間").pack(side='left')
        self.preview_m = tk.Spinbox(time_frame, from_=0, to=59, width=3, format="%02.0f")
        self.preview_m.pack(side='left', padx=2)
        tk.Label(time_frame, text="分").pack(side='left')
        self.preview_s = tk.Spinbox(time_frame, from_=0, to=59, width=3, format="%02.0f")
        self.preview_s.pack(side='left', padx=2)
        tk.Label(time_frame, text="秒").pack(side='left')
        self.preview_ms = tk.Spinbox(time_frame, from_=0, to=999, width=4, format="%03.0f")
        self.preview_ms.pack(side='left', padx=2)
        tk.Label(time_frame, text="ミリ秒").pack(side='left')
        
        tk.Button(time_frame, text="フレーム更新", command=self.update_frame).pack(side='left', padx=10)
        
        # 説明文
        info_label = tk.Label(self.window, text="※ 青い点をドラッグして台形の4つの角を調整してください", fg='blue')
        info_label.pack(pady=5)
        
        # キャンバスフレーム
        canvas_frame = tk.Frame(self.window)
        canvas_frame.pack(pady=10, fill='both', expand=True, padx=10)
        
        # スクロールバー付きキャンバス
        self.canvas = tk.Canvas(canvas_frame, bg='black')
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # マウスイベントをバインド
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        # ボタンフレーム
        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="リセット", command=self.reset_points).pack(side='left', padx=5)
        tk.Button(button_frame, text="プレビュー", command=self.preview_correction).pack(side='left', padx=5)
        tk.Button(button_frame, text="適用", command=self.apply_points, bg='lightgreen').pack(side='left', padx=5)
        tk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side='left', padx=5)
    
    def load_initial_frame(self):
        """初期フレームを読み込み"""
        self.update_frame()
    
    def get_preview_time(self):
        """プレビュー時間を秒で取得（ミリ秒対応）"""
        return (int(self.preview_h.get()) * 3600 + 
                int(self.preview_m.get()) * 60 + 
                int(self.preview_s.get()) + 
                int(self.preview_ms.get()) / 1000.0)
    
    def update_frame(self):
        """指定時間のフレームを更新"""
        try:
            preview_time = self.get_preview_time()
            if preview_time > self.video_info['duration']:
                messagebox.showerror("エラー", "指定時間が動画の長さを超えています")
                return
            
            cap = cv2.VideoCapture(self.video_path)
            
            # 指定時間のフレームに移動
            frame_number = int(preview_time * self.video_info['fps'])
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                self.current_frame = frame
                self.display_frame_on_canvas()
                self.initialize_points()
            else:
                messagebox.showerror("エラー", "フレームの読み込みに失敗しました")
                
        except Exception as e:
            messagebox.showerror("エラー", f"フレーム更新エラー: {str(e)}")
    
    def display_frame_on_canvas(self):
        """フレームをキャンバスに表示"""
        if self.current_frame is None:
            return
        
        # フレームをRGBに変換
        frame_rgb = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
        
        # キャンバスサイズに合わせてスケール計算
        canvas_width = 700
        canvas_height = 500
        
        frame_height, frame_width = frame_rgb.shape[:2]
        
        # アスペクト比を保持してスケール計算
        scale_w = canvas_width / frame_width
        scale_h = canvas_height / frame_height
        self.scale_factor = min(scale_w, scale_h)
        
        new_width = int(frame_width * self.scale_factor)
        new_height = int(frame_height * self.scale_factor)
        
        # リサイズ
        frame_resized = cv2.resize(frame_rgb, (new_width, new_height))
        
        # PIL Imageに変換
        pil_image = Image.fromarray(frame_resized)
        self.display_frame = ImageTk.PhotoImage(pil_image)
        
        # キャンバスクリアして画像表示
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.display_frame)
        
        # キャンバスのスクロール領域を設定
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def initialize_points(self):
        """初期の4点を設定"""
        if self.current_frame is None:
            return
        
        frame_height, frame_width = self.current_frame.shape[:2]
        
        # 現在の座標を取得（メインウィンドウから）
        try:
            current_points = [
                (float(self.point_entries[0][0].get()), float(self.point_entries[0][1].get())),  # 左上
                (float(self.point_entries[1][0].get()), float(self.point_entries[1][1].get())),  # 右上
                (float(self.point_entries[2][0].get()), float(self.point_entries[2][1].get())),  # 左下
                (float(self.point_entries[3][0].get()), float(self.point_entries[3][1].get()))   # 右下
            ]
        except:
            # デフォルト値を使用
            current_points = [
                (0, 0),
                (frame_width, 0),
                (0, frame_height),
                (frame_width, frame_height)
            ]
        
        # スケールを適用した座標に変換
        self.points = []
        for x, y in current_points:
            scaled_x = x * self.scale_factor
            scaled_y = y * self.scale_factor
            self.points.append([scaled_x, scaled_y])
        
        self.draw_points()
    
    def draw_points(self):
        """4点と台形を描画"""
        # 既存の点と線を削除
        self.canvas.delete("point")
        self.canvas.delete("line")
        
        if len(self.points) != 4:
            return
        
        # 台形の線を描画
        for i in range(4):
            start = self.points[i]
            end = self.points[(i + 1) % 4]
            self.canvas.create_line(start[0], start[1], end[0], end[1], 
                                  fill="red", width=2, tags="line")
        
        # 点を描画
        point_labels = ["左上", "右上", "左下", "右下"]
        for i, (x, y) in enumerate(self.points):
            # 点の円
            self.canvas.create_oval(x-8, y-8, x+8, y+8, 
                                  fill="blue", outline="white", width=2, tags="point")
            # ラベル
            self.canvas.create_text(x, y-15, text=point_labels[i], 
                                  fill="yellow", font=("Arial", 10, "bold"), tags="point")
    
    def on_canvas_click(self, event):
        """キャンバスクリック時の処理"""
        # 最も近い点を見つける
        click_x = self.canvas.canvasx(event.x)
        click_y = self.canvas.canvasy(event.y)
        
        min_distance = float('inf')
        closest_point = None
        
        for i, (x, y) in enumerate(self.points):
            distance = ((click_x - x) ** 2 + (click_y - y) ** 2) ** 0.5
            if distance < 20 and distance < min_distance:  # 20ピクセル以内
                min_distance = distance
                closest_point = i
        
        self.dragging_point = closest_point
    
    def on_canvas_drag(self, event):
        """ドラッグ時の処理"""
        if self.dragging_point is not None:
            # 新しい座標を取得
            new_x = self.canvas.canvasx(event.x)
            new_y = self.canvas.canvasy(event.y)
            
            # 画像の範囲内に制限
            if self.display_frame:
                new_x = max(0, min(new_x, self.display_frame.width()))
                new_y = max(0, min(new_y, self.display_frame.height()))
            
            # 点の座標を更新
            self.points[self.dragging_point] = [new_x, new_y]
            self.draw_points()
    
    def on_canvas_release(self, event):
        """ドラッグ終了時の処理"""
        self.dragging_point = None
    
    def reset_points(self):
        """点をリセット"""
        if self.current_frame is None:
            return
        
        frame_height, frame_width = self.current_frame.shape[:2]
        
        # デフォルト座標をスケール適用して設定
        default_points = [
            (0, 0),
            (frame_width, 0),
            (0, frame_height),
            (frame_width, frame_height)
        ]
        
        self.points = []
        for x, y in default_points:
            scaled_x = x * self.scale_factor
            scaled_y = y * self.scale_factor
            self.points.append([scaled_x, scaled_y])
        
        self.draw_points()
    
    def preview_correction(self):
        """台形補正のプレビューを表示"""
        if self.current_frame is None or len(self.points) != 4:
            messagebox.showerror("エラー", "フレームまたは点が設定されていません")
            return
        
        try:
            # 元の座標に変換
            src_points = np.float32([
                [p[0] / self.scale_factor, p[1] / self.scale_factor] for p in self.points
            ])
            
            frame_height, frame_width = self.current_frame.shape[:2]
            dst_points = np.float32([
                [0, 0],
                [frame_width, 0],
                [0, frame_height],
                [frame_width, frame_height]
            ])
            
            # 透視変換を適用
            matrix = cv2.getPerspectiveTransform(src_points, dst_points)
            corrected = cv2.warpPerspective(self.current_frame, matrix, (frame_width, frame_height))
            
            # プレビューウィンドウを作成
            preview_window = tk.Toplevel(self.window)
            preview_window.title("台形補正プレビュー")
            preview_window.geometry("800x600")
            
            # プレビュー用キャンバス
            preview_canvas = tk.Canvas(preview_window, bg='black')
            preview_canvas.pack(fill='both', expand=True)
            
            # 補正後画像を表示
            corrected_rgb = cv2.cvtColor(corrected, cv2.COLOR_BGR2RGB)
            
            # ウィンドウサイズに合わせてリサイズ
            preview_scale = min(750 / frame_width, 550 / frame_height)
            preview_width = int(frame_width * preview_scale)
            preview_height = int(frame_height * preview_scale)
            
            corrected_resized = cv2.resize(corrected_rgb, (preview_width, preview_height))
            pil_preview = Image.fromarray(corrected_resized)
            preview_image = ImageTk.PhotoImage(pil_preview)
            
            preview_canvas.create_image(10, 10, anchor="nw", image=preview_image)
            
            # 画像の参照を保持
            preview_canvas.image = preview_image
            
        except Exception as e:
            messagebox.showerror("エラー", f"プレビュー生成エラー: {str(e)}")
    
    def apply_points(self):
        """設定した点をメインウィンドウに適用"""
        if len(self.points) != 4:
            messagebox.showerror("エラー", "4つの点が設定されていません")
            return
        
        # 元の座標に変換してメインウィンドウに設定
        for i, (x, y) in enumerate(self.points):
            original_x = x / self.scale_factor
            original_y = y / self.scale_factor
            
            self.point_entries[i][0].delete(0, tk.END)
            self.point_entries[i][0].insert(0, str(int(original_x)))
            self.point_entries[i][1].delete(0, tk.END)
            self.point_entries[i][1].insert(0, str(int(original_y)))
        
        messagebox.showinfo("完了", "台形補正の座標が適用されました")
        self.window.destroy()
    
    def cancel(self):
        """キャンセル"""
        self.window.destroy()


class VideoEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("超簡単動画編集アプリ (GPU対応)")
        self.root.geometry("650x850")  # 縦を100ピクセル拡大
        
        self.video_path = None
        self.video_info = None
        self.perspective_points = []
        self.available_gpus = self.detect_gpu_support()
        
        self.setup_ui()
    
    def detect_gpu_support(self):
        """利用可能なGPUエンコーダーを検出"""
        gpu_options = []
        
        try:
            # ffmpegの存在確認
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                                  timeout=10)
            
            if result.returncode != 0:
                print("ffmpegが見つかりません")
                return [('CPU (OpenCV)', 'opencv')]
            
            print("ffmpeg検出成功")
            
            # NVIDIA GPU情報を詳しく確認
            try:
                nvidia_smi = subprocess.run(['nvidia-smi'], capture_output=True, text=True,
                                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                                          timeout=10)
                if nvidia_smi.returncode == 0:
                    print("NVIDIA GPU検出:", nvidia_smi.stdout.split('\n')[8:12])  # GPU情報行
                else:
                    print("nvidia-smi実行失敗またはNVIDIA GPUなし")
            except:
                print("nvidia-smi not found - NVIDIA GPUが無いか、ドライバー未インストール")
            
            # エンコーダー一覧を取得
            result = subprocess.run(['ffmpeg', '-encoders'], 
                                  capture_output=True, text=True, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                                  timeout=10)
            encoders = result.stdout
            print("利用可能エンコーダー確認中...")
            
            # NVENC詳細テスト
            if 'h264_nvenc' in encoders:
                print("h264_nvenc がエンコーダーリストに存在")
                
                # より詳細なNVENCテスト（エラー情報付き）
                test_cmd = ['ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=0.1:size=320x240:rate=1', 
                           '-c:v', 'h264_nvenc', '-preset', 'fast', '-f', 'null', '-', '-v', 'error']
                try:
                    test_result = subprocess.run(test_cmd, capture_output=True, text=True, 
                                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                                               timeout=15)
                    
                    if test_result.returncode == 0:
                        gpu_options.append(('NVIDIA GPU (H.264)', 'h264_nvenc'))
                        print("✅ NVENC H.264 使用可能")
                    else:
                        print(f"❌ NVENC H.264 テスト失敗:")
                        print(f"stderr: {test_result.stderr}")
                        # 詳細なエラー分析
                        if "Driver does not support the required nvenc API version" in test_result.stderr:
                            print("→ NVIDIAドライバーが古すぎます")
                        elif "Cannot load nvcuda.dll" in test_result.stderr:
                            print("→ CUDA ドライバーの問題")
                        elif "No NVENC capable devices found" in test_result.stderr:
                            print("→ NVENC対応GPUが見つかりません")
                        else:
                            print("→ その他のNVENC問題")
                            
                except subprocess.TimeoutExpired:
                    print("❌ NVENC テストがタイムアウト")
                except Exception as e:
                    print(f"❌ NVENC テスト例外: {e}")
            else:
                print("h264_nvenc がエンコーダーリストに存在しません")
            
            # H.265 NVENC テスト
            if 'hevc_nvenc' in encoders:
                test_cmd = ['ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=0.1:size=320x240:rate=1', 
                           '-c:v', 'hevc_nvenc', '-preset', 'fast', '-f', 'null', '-', '-v', 'error']
                try:
                    test_result = subprocess.run(test_cmd, capture_output=True, text=True, 
                                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                                               timeout=15)
                    if test_result.returncode == 0:
                        gpu_options.append(('NVIDIA GPU (H.265)', 'hevc_nvenc'))
                        print("✅ NVENC H.265 使用可能")
                    else:
                        print(f"❌ NVENC H.265 テスト失敗: {test_result.stderr}")
                except:
                    print("❌ NVENC H.265 テスト例外")
            
            # Intel QuickSync テスト
            if 'h264_qsv' in encoders:
                test_cmd = ['ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=0.1:size=320x240:rate=1', 
                           '-c:v', 'h264_qsv', '-f', 'null', '-', '-v', 'error']
                try:
                    test_result = subprocess.run(test_cmd, capture_output=True, text=True, 
                                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                                               timeout=15)
                    if test_result.returncode == 0:
                        gpu_options.append(('Intel QuickSync (H.264)', 'h264_qsv'))
                        print("✅ Intel QSV H.264 使用可能")
                    else:
                        print(f"❌ Intel QSV H.264 使用不可: {test_result.stderr}")
                except:
                    print("❌ Intel QSV テスト例外")
                    
            if 'hevc_qsv' in encoders:
                gpu_options.append(('Intel QuickSync (H.265)', 'hevc_qsv'))
            
            # CPU エンコーダー
            if 'libx264' in encoders:
                gpu_options.append(('CPU (H.264)', 'libx264'))
                print("✅ CPU H.264 使用可能")
                
        except subprocess.TimeoutExpired:
            print("ffmpegコマンドがタイムアウトしました")
        except FileNotFoundError:
            print("ffmpegが見つかりません。")
        except Exception as e:
            print(f"GPU検出エラー: {e}")
        
        # OpenCV フォールバック（最も安全）
        gpu_options.append(('CPU (OpenCV)', 'opencv'))
        print("✅ CPU OpenCV 使用可能")
        
        return gpu_options if gpu_options else [('CPU (OpenCV)', 'opencv')]
    
    def setup_ui(self):
        # ファイル選択
        file_frame = tk.Frame(self.root)
        file_frame.pack(pady=10, fill='x', padx=10)
        
        tk.Button(file_frame, text="動画ファイルを選択", command=self.select_video).pack(side='left')
        self.file_label = tk.Label(file_frame, text="ファイルが選択されていません", fg='gray')
        self.file_label.pack(side='left', padx=(10, 0))
        
        # GPU設定とディagnostic
        gpu_frame = tk.LabelFrame(self.root, text="エンコード設定")
        gpu_frame.pack(pady=10, fill='x', padx=10)
        
        tk.Label(gpu_frame, text="エンコーダー:").pack(anchor='w', padx=10, pady=2)
        self.encoder_var = tk.StringVar()
        self.encoder_combo = ttk.Combobox(gpu_frame, textvariable=self.encoder_var, 
                                         values=[option[0] for option in self.available_gpus],
                                         state='readonly')
        self.encoder_combo.pack(fill='x', padx=10, pady=2)
        if self.available_gpus:
            self.encoder_combo.current(0)  # 最初のオプションを選択
        
        # 診断ボタンを追加
        diag_frame = tk.Frame(gpu_frame)
        diag_frame.pack(fill='x', padx=10, pady=2)
        tk.Button(diag_frame, text="🔍 GPU診断", command=self.show_gpu_diagnostics, 
                 bg='lightcyan').pack(side='left')
        self.diag_label = tk.Label(diag_frame, text="", fg='blue', font=('Arial', 8))
        self.diag_label.pack(side='left', padx=10)
        
        # 品質設定
        quality_frame = tk.Frame(gpu_frame)
        quality_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(quality_frame, text="品質:").pack(side='left')
        self.quality_var = tk.StringVar(value="高品質")
        quality_combo = ttk.Combobox(quality_frame, textvariable=self.quality_var,
                                   values=["最高品質", "高品質", "標準品質", "高速"],
                                   state='readonly', width=15)
        quality_combo.pack(side='left', padx=5)
        quality_combo.current(1)
        
        # 動画情報表示
        info_frame = tk.LabelFrame(self.root, text="動画情報")
        info_frame.pack(pady=10, fill='x', padx=10)
        
        self.duration_label = tk.Label(info_frame, text="合計時間: --")
        self.duration_label.pack(anchor='w', padx=10, pady=5)
        
        self.resolution_label = tk.Label(info_frame, text="画質: --")
        self.resolution_label.pack(anchor='w', padx=10, pady=5)
        
        # 切り抜き設定
        trim_frame = tk.LabelFrame(self.root, text="切り抜き設定")
        trim_frame.pack(pady=10, fill='x', padx=10)
        
        start_frame = tk.Frame(trim_frame)
        start_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(start_frame, text="開始時間:").pack(side='left')
        self.start_h = tk.Spinbox(start_frame, from_=0, to=23, width=3, format="%02.0f")
        self.start_h.pack(side='left', padx=2)
        tk.Label(start_frame, text="時間").pack(side='left')
        self.start_m = tk.Spinbox(start_frame, from_=0, to=59, width=3, format="%02.0f")
        self.start_m.pack(side='left', padx=2)
        tk.Label(start_frame, text="分").pack(side='left')
        self.start_s = tk.Spinbox(start_frame, from_=0, to=59, width=3, format="%02.0f")
        self.start_s.pack(side='left', padx=2)
        tk.Label(start_frame, text="秒").pack(side='left')
        self.start_ms = tk.Spinbox(start_frame, from_=0, to=999, width=4, format="%03.0f")
        self.start_ms.pack(side='left', padx=2)
        tk.Label(start_frame, text="ミリ秒").pack(side='left')
        
        end_frame = tk.Frame(trim_frame)
        end_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(end_frame, text="終了時間:").pack(side='left')
        self.end_h = tk.Spinbox(end_frame, from_=0, to=23, width=3, format="%02.0f")
        self.end_h.pack(side='left', padx=2)
        tk.Label(end_frame, text="時間").pack(side='left')
        self.end_m = tk.Spinbox(end_frame, from_=0, to=59, width=3, format="%02.0f")
        self.end_m.pack(side='left', padx=2)
        tk.Label(end_frame, text="分").pack(side='left')
        self.end_s = tk.Spinbox(end_frame, from_=0, to=59, width=3, format="%02.0f")
        self.end_s.pack(side='left', padx=2)
        tk.Label(end_frame, text="秒").pack(side='left')
        self.end_ms = tk.Spinbox(end_frame, from_=0, to=999, width=4, format="%03.0f")
        self.end_ms.pack(side='left', padx=2)
        tk.Label(end_frame, text="ミリ秒").pack(side='left')
        
        # 台形補正設定（オプション）
        perspective_frame = tk.LabelFrame(self.root, text="台形補正設定（オプション）")
        perspective_frame.pack(pady=10, fill='x', padx=10)
        
        self.use_perspective = tk.BooleanVar()
        tk.Checkbutton(perspective_frame, text="台形補正を使用", variable=self.use_perspective).pack(anchor='w', padx=10, pady=5)
        
        # 視覚的設定ボタン
        visual_button_frame = tk.Frame(perspective_frame)
        visual_button_frame.pack(fill='x', padx=10, pady=5)
        
        self.visual_button = tk.Button(visual_button_frame, text="📷 視覚的に設定", 
                                     command=self.open_thumbnail_editor, bg='lightblue',
                                     state='disabled')
        self.visual_button.pack(side='left')
        
        tk.Label(visual_button_frame, text="← 動画を選択後に使用可能", fg='gray').pack(side='left', padx=10)
        
        points_frame = tk.Frame(perspective_frame)
        points_frame.pack(fill='x', padx=10, pady=5)
        
        # 4点の座標入力
        self.point_entries = []
        point_labels = ["左上", "右上", "左下", "右下"]
        for i, label in enumerate(point_labels):
            point_frame = tk.Frame(points_frame)
            point_frame.pack(fill='x', pady=2)
            tk.Label(point_frame, text=f"{label}:", width=6).pack(side='left')
            tk.Label(point_frame, text="X:").pack(side='left')
            x_entry = tk.Entry(point_frame, width=6)
            x_entry.pack(side='left', padx=2)
            tk.Label(point_frame, text="Y:").pack(side='left')
            y_entry = tk.Entry(point_frame, width=6)
            y_entry.pack(side='left', padx=2)
            self.point_entries.append((x_entry, y_entry))
        
        # 進捗表示
        progress_frame = tk.LabelFrame(self.root, text="進捗")
        progress_frame.pack(pady=10, fill='x', padx=10)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill='x', padx=10, pady=5)
        
        self.progress_label = tk.Label(progress_frame, text="待機中...")
        self.progress_label.pack(padx=10, pady=5)
        
        # 実行ボタン
        tk.Button(self.root, text="動画を処理", command=self.process_video, bg='lightgreen').pack(pady=20)
    
    def select_video(self):
        file_path = filedialog.askopenfilename(
            title="動画ファイルを選択",
            filetypes=[("動画ファイル", "*.mp4 *.avi *.mov *.mkv *.wmv")]
        )
        if file_path:
            self.video_path = file_path
            self.file_label.config(text=os.path.basename(file_path), fg='black')
            self.get_video_info()
            # 視覚的設定ボタンを有効化
            self.visual_button.config(state='normal')
    
    def get_video_info(self):
        try:
            # OpenCVを使用して動画情報を取得
            cap = cv2.VideoCapture(self.video_path)
            
            if not cap.isOpened():
                raise Exception("動画ファイルを開けません")
            
            # 動画情報を取得
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 総時間を計算
            duration = frame_count / fps if fps > 0 else 0
            duration_str = str(timedelta(seconds=int(duration)))
            
            cap.release()
            
            # 情報を表示
            self.duration_label.config(text=f"合計時間: {duration_str}")
            self.resolution_label.config(text=f"画質: {width}x{height}")
            
            # デフォルトの台形補正座標を設定
            default_coords = [
                ("0", "0"),           # 左上
                (str(width), "0"),    # 右上
                ("0", str(height)),   # 左下
                (str(width), str(height))  # 右下
            ]
            
            for i, (x, y) in enumerate(default_coords):
                self.point_entries[i][0].delete(0, tk.END)
                self.point_entries[i][0].insert(0, x)
                self.point_entries[i][1].delete(0, tk.END)
                self.point_entries[i][1].insert(0, y)
            
            self.video_info = {
                'width': width,
                'height': height,
                'fps': fps,
                'duration': duration,
                'frame_count': frame_count
            }
            
        except Exception as e:
            messagebox.showerror("エラー", f"動画情報の取得に失敗しました: {str(e)}")
            print(f"詳細エラー: {e}")
    
    def show_gpu_diagnostics(self):
        """GPU診断情報を表示するウィンドウ"""
        diag_window = tk.Toplevel(self.root)
        diag_window.title("GPU診断情報")
        diag_window.geometry("700x500")
        
        # スクロール可能なテキストエリア
        text_frame = tk.Frame(diag_window)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side='right', fill='y')
        
        text_area = tk.Text(text_frame, yscrollcommand=scrollbar.set, font=('Consolas', 9))
        text_area.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=text_area.yview)
        
        # 診断情報を収集
        diag_info = "=== GPU診断レポート ===\n\n"
        
        try:
            # システム情報
            diag_info += "1. システム情報\n"
            diag_info += f"OS: {os.name}\n"
            
            # NVIDIA GPU確認
            diag_info += "\n2. NVIDIA GPU確認\n"
            try:
                nvidia_smi = subprocess.run(['nvidia-smi', '--query-gpu=name,driver_version,cuda_version', '--format=csv'], 
                                          capture_output=True, text=True,
                                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                                          timeout=10)
                if nvidia_smi.returncode == 0:
                    diag_info += nvidia_smi.stdout
                else:
                    diag_info += "nvidia-smi実行失敗\n"
            except FileNotFoundError:
                diag_info += "nvidia-smi not found (NVIDIAドライバー未インストール?)\n"
            except Exception as e:
                diag_info += f"nvidia-smi エラー: {e}\n"
            
            # ffmpeg バージョン
            diag_info += "\n3. ffmpeg情報\n"
            try:
                ffmpeg_ver = subprocess.run(['ffmpeg', '-version'], 
                                          capture_output=True, text=True,
                                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                                          timeout=10)
                if ffmpeg_ver.returncode == 0:
                    # 最初の数行のみ表示
                    lines = ffmpeg_ver.stdout.split('\n')[:5]
                    diag_info += '\n'.join(lines) + '\n'
                else:
                    diag_info += "ffmpeg バージョン取得失敗\n"
            except Exception as e:
                diag_info += f"ffmpeg エラー: {e}\n"
            
            # エンコーダー確認
            diag_info += "\n4. エンコーダー確認\n"
            try:
                encoders = subprocess.run(['ffmpeg', '-encoders'], 
                                        capture_output=True, text=True,
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                                        timeout=10)
                if encoders.returncode == 0:
                    # NVENC関連エンコーダーのみ抽出
                    for line in encoders.stdout.split('\n'):
                        if 'nvenc' in line.lower() or 'h264' in line.lower() or 'hevc' in line.lower():
                            diag_info += line + '\n'
                else:
                    diag_info += "エンコーダー一覧取得失敗\n"
            except Exception as e:
                diag_info += f"エンコーダー確認エラー: {e}\n"
            
            # NVENC詳細テスト
            diag_info += "\n5. NVENC詳細テスト\n"
            test_cmd = ['ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=0.1:size=320x240:rate=1', 
                       '-c:v', 'h264_nvenc', '-preset', 'fast', '-f', 'null', '-']
            try:
                test_result = subprocess.run(test_cmd, capture_output=True, text=True,
                                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                                           timeout=15)
                diag_info += f"テストコマンド: {' '.join(test_cmd)}\n"
                diag_info += f"戻り値: {test_result.returncode}\n"
                if test_result.stderr:
                    diag_info += f"エラー出力:\n{test_result.stderr}\n"
                if test_result.stdout:
                    diag_info += f"標準出力:\n{test_result.stdout}\n"
            except Exception as e:
                diag_info += f"NVENCテストエラー: {e}\n"
            
            # 推奨解決策
            diag_info += "\n6. 推奨解決策\n"
            diag_info += "A. NVIDIAドライバー更新:\n"
            diag_info += "   - https://www.nvidia.com/drivers/ から最新版をダウンロード\n"
            diag_info += "   - GeForce Experience経由でも更新可能\n\n"
            diag_info += "B. CUDA Toolkitインストール:\n"
            diag_info += "   - https://developer.nvidia.com/cuda-downloads\n\n"
            diag_info += "C. 代替エンコーダー使用:\n"
            diag_info += "   - 'CPU (H.264)' または 'CPU (OpenCV)' を選択\n"
            diag_info += "   - 品質は同等、速度は若干遅くなります\n\n"
            
        except Exception as e:
            diag_info += f"\n診断中にエラーが発生: {e}\n"
        
        # テキストエリアに表示
        text_area.insert('1.0', diag_info)
        text_area.config(state='disabled')  # 読み取り専用
        
        # 簡易診断結果をメインウィンドウにも表示
        if "nvidia-smi not found" in diag_info:
            self.diag_label.config(text="NVIDIAドライバー未検出")
        elif "戻り値: 0" in diag_info:
            self.diag_label.config(text="NVENC利用可能", fg='green')
        else:
            self.diag_label.config(text="NVENC利用不可 (詳細は診断ウィンドウ参照)", fg='red')
    
    def open_thumbnail_editor(self):
        """サムネイル編集ウィンドウを開く"""
        if not self.video_path or not self.video_info:
            messagebox.showerror("エラー", "動画ファイルを選択してください")
            return
        
        ThumbnailEditor(self.root, self.video_path, self.video_info, self.point_entries)
    
    def get_time_in_seconds(self, h_spinbox, m_spinbox, s_spinbox, ms_spinbox=None):
        """時間を秒に変換（ミリ秒対応）"""
        seconds = int(h_spinbox.get()) * 3600 + int(m_spinbox.get()) * 60 + int(s_spinbox.get())
        if ms_spinbox is not None:
            seconds += int(ms_spinbox.get()) / 1000.0
        return seconds
    
    def get_encoder_settings(self):
        """選択されたエンコーダーに基づいて設定を返す"""
        encoder_name = self.encoder_var.get()
        encoder_code = None
        
        for name, code in self.available_gpus:
            if name == encoder_name:
                encoder_code = code
                break
        
        if not encoder_code:
            encoder_code = 'opencv'  # デフォルト
        
        quality = self.quality_var.get()
        
        # OpenCVの場合は品質設定を返す
        if encoder_code == 'opencv':
            quality_map = {
                "最高品質": 95,
                "高品質": 85,
                "標準品質": 75,
                "高速": 65
            }
            return encoder_code, quality_map.get(quality, 85)
        
        # ffmpeg用の品質設定（シンプル化）
        if 'nvenc' in encoder_code:
            # NVIDIA GPU設定 - より安定した設定
            quality_map = {
                "最高品質": ['-preset', 'slow', '-cq', '18'],
                "高品質": ['-preset', 'medium', '-cq', '23'],
                "標準品質": ['-preset', 'fast', '-cq', '28'],
                "高速": ['-preset', 'ultrafast', '-cq', '30']
            }
        elif 'qsv' in encoder_code:
            # Intel QuickSync設定
            quality_map = {
                "最高品質": ['-preset', 'veryslow', '-global_quality', '18'],
                "高品質": ['-preset', 'medium', '-global_quality', '23'],
                "標準品質": ['-preset', 'fast', '-global_quality', '28'],
                "高速": ['-preset', 'ultrafast', '-global_quality', '30']
            }
        else:
            # CPU設定
            quality_map = {
                "最高品質": ['-preset', 'veryslow', '-crf', '18'],
                "高品質": ['-preset', 'medium', '-crf', '23'],
                "標準品質": ['-preset', 'fast', '-crf', '28'],
                "高速": ['-preset', 'ultrafast', '-crf', '30']
            }
        
        return encoder_code, quality_map.get(quality, quality_map["高品質"])
    
    def process_video_opencv(self, output_path, start_time, end_time, quality):
        """OpenCVを使用した動画処理"""
        try:
            cap = cv2.VideoCapture(self.video_path)
            
            if not cap.isOpened():
                raise Exception("動画ファイルを開けません")
            
            # 動画情報
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 開始・終了フレームを計算
            start_frame = int(start_time * fps)
            end_frame = int(end_time * fps)
            total_frames = end_frame - start_frame
            
            # 開始フレームに移動
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            # 出力設定
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            # 台形補正の準備
            use_correction = self.use_perspective.get()
            if use_correction:
                try:
                    src_points = np.float32([
                        [float(self.point_entries[0][0].get()), float(self.point_entries[0][1].get())],  # 左上
                        [float(self.point_entries[1][0].get()), float(self.point_entries[1][1].get())],  # 右上
                        [float(self.point_entries[2][0].get()), float(self.point_entries[2][1].get())],  # 左下
                        [float(self.point_entries[3][0].get()), float(self.point_entries[3][1].get())]   # 右下
                    ])
                    dst_points = np.float32([
                        [0, 0],
                        [width, 0],
                        [0, height],
                        [width, height]
                    ])
                    perspective_matrix = cv2.getPerspectiveTransform(src_points, dst_points)
                except ValueError:
                    raise Exception("台形補正の座標が正しくありません")
            
            processed_frames = 0
            start_process_time = time.time()
            
            while processed_frames < total_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 台形補正を適用
                if use_correction:
                    frame = cv2.warpPerspective(frame, perspective_matrix, (width, height))
                
                out.write(frame)
                processed_frames += 1
                
                # 進捗を更新
                if processed_frames % 30 == 0:  # 30フレームごとに更新
                    progress = (processed_frames / total_frames) * 100
                    elapsed_time = time.time() - start_process_time
                    if processed_frames > 0:
                        remaining_time = (elapsed_time / processed_frames) * (total_frames - processed_frames)
                        remaining_str = str(timedelta(seconds=int(remaining_time)))
                    else:
                        remaining_str = "計算中..."
                    
                    self.root.after(0, lambda p=progress, r=remaining_str: 
                                  self.update_progress(p, f"処理中 - 残り: {r}"))
            
            cap.release()
            out.release()
            return True
            
        except Exception as e:
            print(f"OpenCV処理エラー: {e}")
            return False
    
    def process_video_ffmpeg(self, output_path, start_time, end_time, encoder, quality_settings):
        """ffmpegを使用した動画処理（音声対応、GPU最適化）"""
        try:
            # 台形補正が必要な場合は、先にffmpegで台形補正を適用
            if self.use_perspective.get():
                return self.process_video_ffmpeg_with_perspective(output_path, start_time, end_time, encoder, quality_settings)
            
            cmd = ['ffmpeg', '-y']  # -y で上書き確認をスキップ
            
            # ハードウェアデコードを控えめに設定（互換性重視）
            if 'nvenc' in encoder:
                # NVIDIAの場合はソフトウェアデコード＋ハードウェアエンコード
                pass  # ハードウェアデコードは使わない
            elif 'qsv' in encoder:
                # Intel QSVも同様
                pass
            
            # 入力ファイルと範囲指定
            cmd.extend(['-i', self.video_path, '-ss', str(start_time), '-t', str(end_time - start_time)])
            
            # エンコーダー設定
            cmd.extend(['-c:v', encoder])
            
            # 音声設定（元の音声を保持）
            cmd.extend(['-c:a', 'copy'])  # 音声をそのままコピー（高速＋品質保持）
            
            # 品質設定を追加
            if quality_settings:
                cmd.extend(quality_settings)
            
            # ピクセルフォーマット指定（互換性向上）
            cmd.extend(['-pix_fmt', 'yuv420p'])
            
            # 出力ファイル
            cmd.append(output_path)
            
            print(f"実行コマンド: {' '.join(cmd)}")  # デバッグ用
            
            # ffmpeg実行
            self.root.after(0, lambda: self.progress_label.config(text="エンコード中..."))
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            # プロセス完了を待機
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                print(f"ffmpegエラー詳細: {error_msg}")
                raise Exception(f"ffmpegエンコードエラー: {error_msg}")
            
            print("エンコード完了")
            return True
            
        except Exception as e:
            print(f"ffmpeg処理エラー: {e}")
            return False
    
    def process_video_ffmpeg_with_perspective(self, output_path, start_time, end_time, encoder, quality_settings):
        """ffmpegで台形補正を含む動画処理（GPUエンコード対応）"""
        try:
            # 台形補正の座標を取得
            src_points = []
            try:
                for i in range(4):
                    x = float(self.point_entries[i][0].get())
                    y = float(self.point_entries[i][1].get())
                    src_points.append((x, y))
            except ValueError:
                raise Exception("台形補正の座標が正しくありません")
            
            # まずはOpenCVでのフォールバック処理を直接実行
            # ffmpegのperspectiveフィルターは複雑すぎるため
            print("台形補正: OpenCV方式を使用します")
            return self.process_video_opencv_fallback(output_path, start_time, end_time, encoder, quality_settings)
            
        except Exception as e:
            print(f"台形補正処理エラー: {e}")
            # エラーの場合もOpenCVにフォールバック
            print("OpenCVでの処理にフォールバックします...")
            return self.process_video_opencv_fallback(output_path, start_time, end_time, encoder, quality_settings)
    
    def process_video_opencv_fallback(self, output_path, start_time, end_time, encoder, quality_settings):
        """OpenCVで台形補正を行い、その後ffmpegでエンコード"""
        try:
            # 一時ファイルパス
            temp_video_path = output_path.replace('.mp4', '_corrected_temp.mp4')
            
            # OpenCVで台形補正を適用
            self.root.after(0, lambda: self.progress_label.config(text="台形補正を適用中..."))
            
            src_points = np.float32([
                [float(self.point_entries[0][0].get()), float(self.point_entries[0][1].get())],  # 左上
                [float(self.point_entries[1][0].get()), float(self.point_entries[1][1].get())],  # 右上
                [float(self.point_entries[2][0].get()), float(self.point_entries[2][1].get())],  # 左下
                [float(self.point_entries[3][0].get()), float(self.point_entries[3][1].get())]   # 右下
            ])
            dst_points = np.float32([
                [0, 0],
                [self.video_info['width'], 0],
                [0, self.video_info['height']],
                [self.video_info['width'], self.video_info['height']]
            ])
            
            print(f"台形補正座標:")
            print(f"  元座標: {src_points}")
            print(f"  変換後: {dst_points}")
            
            cap = cv2.VideoCapture(self.video_path)
            
            # 指定範囲のフレームのみ処理
            start_frame = int(start_time * self.video_info['fps'])
            end_frame = int(end_time * self.video_info['fps'])
            total_frames = end_frame - start_frame
            
            print(f"処理範囲: フレーム {start_frame} - {end_frame} (合計 {total_frames} フレーム)")
            
            # 開始フレームに移動
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            # 一時動画ファイル作成（映像のみ、高品質）
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video_path, fourcc, self.video_info['fps'],
                                (self.video_info['width'], self.video_info['height']))
            
            if not out.isOpened():
                raise Exception("一時動画ファイルの作成に失敗しました")
            
            processed_frames = 0
            matrix = cv2.getPerspectiveTransform(src_points, dst_points)
            print(f"変換行列: \n{matrix}")
            
            while processed_frames < total_frames:
                ret, frame = cap.read()
                if not ret:
                    print(f"フレーム {processed_frames} の読み込みに失敗")
                    break
                
                # 台形補正を適用
                corrected = cv2.warpPerspective(frame, matrix, 
                                              (self.video_info['width'], self.video_info['height']))
                
                # フレームが真っ黒でないかチェック
                if processed_frames == 0:
                    mean_brightness = np.mean(corrected)
                    print(f"最初のフレームの平均輝度: {mean_brightness}")
                    if mean_brightness < 1:
                        print("警告: 補正後のフレームが真っ黒です")
                
                out.write(corrected)
                processed_frames += 1
                
                if processed_frames % 30 == 0:
                    progress = (processed_frames / total_frames) * 50
                    self.root.after(0, lambda p=progress: self.update_progress(p, f"台形補正中... {processed_frames}/{total_frames}"))
            
            cap.release()
            out.release()
            
            print(f"台形補正完了: {processed_frames} フレーム処理")
            
            # ffmpegで音声を結合してエンコード
            self.root.after(0, lambda: self.progress_label.config(text="音声結合+エンコード中..."))
            
            cmd = ['ffmpeg', '-y',
                   '-i', temp_video_path,  # 台形補正済み映像
                   '-ss', str(start_time), '-t', str(end_time - start_time),
                   '-i', self.video_path]  # 元動画（音声用）
            
            # エンコーダー設定
            cmd.extend(['-c:v', encoder])
            
            # 品質設定
            if quality_settings:
                cmd.extend(quality_settings)
            
            # 音声設定とマッピング
            cmd.extend([
                '-c:a', 'copy',
                '-map', '0:v:0',  # 1番目の入力の映像（台形補正済み）
                '-map', '1:a:0?',  # 2番目の入力の音声（?で音声がない場合も許可）
                '-pix_fmt', 'yuv420p',
                output_path
            ])
            
            print(f"音声結合コマンド: {' '.join(cmd)}")
            
            process = subprocess.run(cmd, capture_output=True, 
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            # 一時ファイル削除
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
            
            if process.returncode != 0:
                error_msg = process.stderr.decode('utf-8', errors='ignore')
                print(f"音声結合エラー: {error_msg}")
                return False
            
            print("音声結合+エンコード完了")
            return True
            
        except Exception as e:
            # 一時ファイルのクリーンアップ
            if 'temp_video_path' in locals() and os.path.exists(temp_video_path):
                try:
                    os.remove(temp_video_path)
                except:
                    pass
            print(f"OpenCVフォールバック処理エラー: {e}")
            return False
    
    def create_temp_video_with_perspective(self, temp_path):
        """台形補正を適用した一時ファイルを作成（音声付き）"""
        try:
            src_points = np.float32([
                [float(self.point_entries[0][0].get()), float(self.point_entries[0][1].get())],  # 左上
                [float(self.point_entries[1][0].get()), float(self.point_entries[1][1].get())],  # 右上
                [float(self.point_entries[2][0].get()), float(self.point_entries[2][1].get())],  # 左下
                [float(self.point_entries[3][0].get()), float(self.point_entries[3][1].get())]   # 右下
            ])
            dst_points = np.float32([
                [0, 0],
                [self.video_info['width'], 0],
                [0, self.video_info['height']],
                [self.video_info['width'], self.video_info['height']]
            ])
            
            cap = cv2.VideoCapture(self.video_path)
            
            # 音声付きで出力するため、ffmpegを使用
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_temp = temp_path.replace('.mp4', '_video_only.mp4')
            out = cv2.VideoWriter(video_temp, fourcc, self.video_info['fps'],
                                (self.video_info['width'], self.video_info['height']))
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            processed_frames = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 透視変換を適用
                matrix = cv2.getPerspectiveTransform(src_points, dst_points)
                corrected = cv2.warpPerspective(frame, matrix, 
                                              (self.video_info['width'], self.video_info['height']))
                out.write(corrected)
                
                processed_frames += 1
                if processed_frames % 30 == 0:  # 30フレームごとに更新
                    progress = (processed_frames / total_frames) * 50  # 台形補正は全体の50%
                    self.root.after(0, lambda p=progress: self.update_progress(p, "台形補正中..."))
            
            cap.release()
            out.release()
            
            # 音声を元の動画から抽出して結合
            audio_cmd = ['ffmpeg', '-y', 
                        '-i', video_temp,  # 映像のみ
                        '-i', self.video_path,  # 元動画（音声用）
                        '-c:v', 'copy',  # 映像をそのままコピー
                        '-c:a', 'copy',  # 音声をそのままコピー
                        '-map', '0:v:0',  # 1番目の入力の映像
                        '-map', '1:a:0',  # 2番目の入力の音声
                        temp_path]
            
            process = subprocess.run(audio_cmd, capture_output=True, 
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            # 一時ファイルを削除
            if os.path.exists(video_temp):
                os.remove(video_temp)
            
            return process.returncode == 0
            
        except Exception as e:
            print(f"台形補正エラー: {e}")
            return False
    
    def process_video(self):
        if not self.video_path:
            messagebox.showerror("エラー", "動画ファイルを選択してください")
            return
        
        # 保存先を選択
        output_path = filedialog.asksaveasfilename(
            title="出力ファイル名を指定",
            defaultextension=".mp4",
            filetypes=[("MP4ファイル", "*.mp4")]
        )
        if not output_path:
            return
        
        # 別スレッドで処理を開始
        thread = threading.Thread(target=self._process_video_thread, args=(output_path,))
        thread.daemon = True
        thread.start()
    
    def _process_video_thread(self, output_path):
        try:
            start_time = self.get_time_in_seconds(self.start_h, self.start_m, self.start_s, self.start_ms)
            end_time = self.get_time_in_seconds(self.end_h, self.end_m, self.end_s, self.end_ms)
            
            if start_time >= end_time:
                self.root.after(0, lambda: messagebox.showerror("エラー", "開始時間は終了時間より前である必要があります"))
                return
            
            if end_time > self.video_info['duration']:
                self.root.after(0, lambda: messagebox.showerror("エラー", "終了時間が動画の長さを超えています"))
                return
            
            # 進捗表示を更新
            self.root.after(0, lambda: self.progress_label.config(text="処理を開始しています..."))
            
            # エンコーダー設定を取得
            encoder, quality_settings = self.get_encoder_settings()
            
            success = False
            
            if encoder == 'opencv':
                # OpenCVで処理
                success = self.process_video_opencv(output_path, start_time, end_time, quality_settings)
            else:
                # ffmpegで処理
                success = self.process_video_ffmpeg(output_path, start_time, end_time, encoder, quality_settings)
            
            if success:
                # 完了通知
                self.root.after(0, lambda: self.progress_label.config(text="完了！"))
                self.root.after(0, lambda: self.progress_bar.config(value=100))
                self.root.after(0, lambda: messagebox.showinfo("完了", f"動画の処理が完了しました！\nエンコーダー: {self.encoder_var.get()}"))
            else:
                raise Exception("動画処理に失敗しました")
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("エラー", f"処理中にエラーが発生しました: {str(e)}"))
            self.root.after(0, lambda: self.progress_label.config(text="エラーが発生しました"))
    
    def parse_time_to_seconds(self, time_str):
        """HH:MM:SS.ss形式の時間を秒に変換"""
        try:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except:
            return 0
    
    def update_progress(self, progress, message):
        self.progress_bar.config(value=min(progress, 100))
        self.progress_label.config(text=message)

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoEditor(root)
    root.mainloop()