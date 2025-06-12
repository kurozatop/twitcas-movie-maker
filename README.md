# Twitcas Movie Maker

![Python](https://img.shields.io/badge/python-v3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)

シンプルで使いやすい動画編集アプリケーションです。GPU加速対応で高速処理が可能、台形補正機能も搭載しています。

## 📋 主な機能

### 🎬 基本機能
- **動画切り抜き**: ミリ秒単位での精密な時間指定
- **GPU加速エンコード**: NVIDIA NVENC、Intel QuickSync対応
- **高品質出力**: H.264/H.265エンコードで最適な品質
- **音声保持**: 元動画の音声を完全に保持

### 🔧 台形補正機能
- **視覚的設定**: ドラッグ&ドロップで直感的に補正点を設定
- **リアルタイムプレビュー**: 補正結果を事前に確認
- **高精度補正**: OpenCV使用で歪みを正確に修正

### ⚡ パフォーマンス
- **GPU診断機能**: 利用可能なハードウェアエンコーダーを自動検出
- **フォールバック機能**: GPU使用不可時は自動的にCPU処理に切り替え
- **進捗表示**: 処理状況をリアルタイムで表示

## 🚀 使用イメージ

このアプリケーションは直感的なGUIインターフェースを提供し、動画編集の専門知識がなくても簡単に高品質な動画処理が可能です。

## 📦 インストール

### 必要要件
- Python 3.7以上
- Windows 10/11 (推奨)
- ffmpeg (必須)

### 依存関係のインストール

```bash
pip install opencv-python numpy pillow tkinter subprocess-run
```

### ffmpegのインストール

1. [Gyan.dev](https://www.gyan.dev/ffmpeg/builds/) より **full** または **essentials** をダウンロード
2. 7-Zipなどで解凍し、任意のディレクトリに配置
3. 当該ディレクトリ/bin をシステム環境変数のPATHに追加

#### 詳細手順（Windows）
1. ダウンロードしたzipファイルを `C:\ffmpeg` に解凍
2. `C:\ffmpeg\bin` をPATHに追加：
   - 「システムのプロパティ」→「環境変数」
   - システム環境変数の「Path」を編集
   - 新規で `C:\ffmpeg\bin` を追加
3. コマンドプロンプトで `ffmpeg -version` を実行して確認

## 🎯 使用方法

### 1. アプリケーション起動
```bash
python twitcas-movie-maker.py
```

### 2. 基本的な動画編集
1. **動画ファイルを選択**ボタンで動画を読み込み
2. 開始時間と終了時間を設定
3. エンコーダーと品質を選択
4. **動画を処理**ボタンで実行

### 3. 台形補正の使用
1. **台形補正を使用**にチェック
2. **📷 視覚的に設定**ボタンをクリック
3. プレビュー画面で青い点をドラッグして補正
4. **プレビュー**で結果確認後、**適用**

### 4. GPU設定の確認
- **🔍 GPU診断**ボタンで利用可能なハードウェアを確認
- 最適なエンコーダーが自動選択されます

## ⚙️ 対応フォーマット

### 入力フォーマット
- MP4, AVI, MOV, MKV, WMV

### 出力フォーマット
- MP4 (H.264/H.265)

### 対応エンコーダー
- **NVIDIA NVENC** (H.264/H.265) - GPU加速
- **Intel QuickSync** (H.264/H.265) - GPU加速  
- **CPU** (H.264) - ソフトウェアエンコード
- **OpenCV** - フォールバック

## 🔧 高度な設定

### 品質設定
- **最高品質**: CRF 18相当、ファイルサイズ大
- **高品質**: CRF 23相当、推奨設定
- **標準品質**: CRF 28相当、バランス型
- **高速**: CRF 30相当、処理優先

### GPU最適化
```python
# NVIDIA GPU設定例
quality_settings = ['-preset', 'medium', '-cq', '23']

# Intel QuickSync設定例  
quality_settings = ['-preset', 'medium', '-global_quality', '23']
```

## 🐛 トラブルシューティング

### GPU が認識されない
1. 最新のグラフィックドライバーを更新
2. NVIDIA の場合: CUDA Toolkit をインストール
3. GPU診断機能で詳細なエラーを確認

### エンコードエラー
1. 入力ファイルの破損チェック
2. 出力先の書き込み権限確認
3. ディスク容量の確認

### 台形補正が効かない
1. 座標が画面範囲内にあるか確認
2. 4点がZ字順になっているか確認
3. プレビュー機能で事前確認

## 📝 開発者向け情報

### プロジェクト構造
```
twitcas-movie-maker/
├── twitcas-movie-maker.py # メインアプリケーション
├── README.md              # このファイル
└── LICENSE                # ライセンス
```

### 主要クラス
- `VideoEditor`: メインアプリケーションクラス
- `ThumbnailEditor`: 台形補正設定ウィンドウ

### カスタマイズ例
```python
# 新しいエンコーダーの追加
def add_custom_encoder(self):
    self.available_gpus.append(('カスタムエンコーダー', 'custom_codec'))
```

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュ (`git push origin feature/AmazingFeature`)
5. プルリクエストを作成

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 👥 作者

- 開発者: 100%Claude4.0 Sonnetくんです。Readmeもこの段落以外全部AI生成です。
- 生成者: https://github.com/kurozatop

## 🙏 謝辞

- [OpenCV](https://opencv.org/) - 画像処理ライブラリ
- [FFmpeg](https://ffmpeg.org/) - 動画処理ライブラリ
- [Python](https://python.org/) - プログラミング言語

## 📊 システム要件

### 最小要件
- CPU: Intel Core i3 / AMD Ryzen 3以上
- RAM: 4GB以上
- ストレージ: 1GB以上の空き容量

### 推奨要件  
- CPU: Intel Core i5 / AMD Ryzen 5以上
- RAM: 8GB以上
- GPU: NVIDIA GTX 1050 / Intel UHD Graphics以上
- ストレージ: SSD推奨

## 🔄 バージョン履歴

### v1.0.0 (2025-06-13)
- 初回リリース
- GPU加速エンコード対応
- 台形補正機能実装
- 視覚的設定インターフェース追加

---

**⭐ このプロジェクトが役立った場合は、GitHubでスターをお願いします！**
