# GrooveRip

<img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white">
<img src="https://img.shields.io/badge/PyQt6-GUI-red?style=for-the-badge&logo=pyqt&logoColor=white">
<img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge">
<img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge">

<img src="assets/icon256.png" width="256" height="256" alt="GrooveRip Icon">

A professional Python GUI tool that allows for easy vinyl recording and digitization with automatic track detection, real-time monitoring, and multi-format export capabilities.

## 🎵 Features

- **Professional Audio Recording**: High-quality vinyl recording with configurable sample rates
- **Automatic Track Detection**: Intelligent silence-based track separation
- **Real-time Monitoring**: Live audio monitoring during recording sessions
- **Multi-format Export**: Support for WAV, FLAC formats (MP3 coming soon)
- **Modern GUI**: Dark-themed interface built with PyQt6
- **Cross-platform**: Works on Windows, Linux, and macOS
- **Configuration Persistence**: Saves your settings between sessions
- **Thread-safe**: Robust multithreading for smooth performance

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Audio recording device (microphone, line-in, or USB audio interface)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/GrooveRip.git
   cd GrooveRip
   ```

2. **Create virtual environment** (recommended):
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

## 📖 Usage Guide

### 1. Setup Your Project

1. **Artist & Album**: Enter the artist name and album title
2. **LP Type**: Choose between LP (2 sides) or 2LP (4 sides)
3. **Side Selection**: Select which side you're recording
4. **Audio Settings**: Configure sample rate and output format
5. **Device Selection**: Choose your recording device from the dropdown
6. **Output Directory**: Select where to save your recordings

### 2. Recording

1. **Enable Monitoring** (optional): Check the box for real-time audio monitoring
2. **Auto-Detect Tracks**: Click to automatically find track boundaries based on silence
3. **Adjust Threshold**: Use the slider to fine-tune silence detection sensitivity
4. **Start Recording**: Click the red button to begin recording
5. **Stop Recording**: Click again when finished

### 3. Track Management

- After recording, GrooveRip will automatically detect tracks
- Name each track in the dialog boxes that appear
- Tracks are listed with their duration
- Each track is saved as a separate file

## 🔧 Technical Details

### Supported Audio Formats

| Format | Quality | Use Case |
|---------|---------|----------|
| **WAV** | Lossless, uncompressed | Maximum quality, large files |
| **FLAC** | Lossless, compressed | High quality, smaller files |
| **MP3** | Lossy, compressed | Small files, good compatibility (coming soon) |

### Sample Rate Options

- **44.1 kHz**: CD Quality (standard)
- **48 kHz**: DVD Quality
- **96 kHz**: High Resolution Audio
- **192 kHz**: Studio Quality

### Track Detection Algorithm

GrooveRip uses an intelligent silence detection algorithm:

1. **Silence Threshold**: Configurable sensitivity (0.001 - 0.100)
2. **Minimum Silence**: 2 seconds of continuous silence required
3. **Minimum Track Length**: 30 seconds minimum per track
4. **Consecutive Silence**: Requires 10 consecutive silent chunks to prevent false positives

## 🛠️ Configuration

GrooveRip automatically saves your settings in `grooverip_config.json`:

- Last used output directory
- Preferred sample rate
- Default audio format
- LP type preference

**Note**: Configuration files are excluded from version control for privacy.

## 🔊 Audio Setup Tips

### Vinyl Recording Setup

1. **Connect your turntable** to your computer's audio input
2. **Use a preamp** if your turntable doesn't have built-in preamplification
3. **Test levels** with the VU meter before recording
4. **Monitor audio** to ensure proper connection

### Recommended Settings

- **Sample Rate**: 48 kHz (good balance of quality and file size)
- **Format**: FLAC (lossless compression)
- **Silence Threshold**: Start with 0.010, adjust as needed

## 🐛 Troubleshooting

### Common Issues

**No audio devices found**:
- Check audio drivers
- Ensure audio device is connected
- Restart application

**Poor audio quality**:
- Check cable connections
- Adjust input levels
- Use proper preamplification

**Track detection not working**:
- Adjust silence threshold slider
- Ensure proper recording levels
- Clean vinyl record

**Application crashes**:
- Check Python version (3.8+ required)
- Install all dependencies: `pip install -r requirements.txt`
- Report issue with system details

### Error Messages

- **"Device Error"**: Selected device cannot record audio
- **"Recording Error"**: Audio system failure during recording
- **"Save Error"**: File system or permission issues

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** your changes: `git commit -m 'Add amazing feature'`
4. **Push** to the branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/GrooveRip.git
cd GrooveRip

# Create virtual environment
python -m venv dev-env
source dev-env/bin/activate  # Linux/macOS
# or
dev-env\Scripts\activate  # Windows

# Install in development mode
pip install -e .

# Run tests (if available)
python -m pytest
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **PyQt6** for the excellent GUI framework
- **sounddevice** for cross-platform audio I/O
- **soundfile** for audio file handling
- **NumPy** for efficient audio processing




