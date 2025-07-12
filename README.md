# MIDI Piano Roll Visualizer / MIDI 钢琴卷帘可视化播放器  

![Screenshot](效果图.png)  

A Python-based MIDI player with piano roll visualization that displays falling notes in real-time.  
一个基于 Python 的 MIDI 文件播放器，带有钢琴卷帘可视化效果，可以实时显示音符下落。  

## Features / 功能特点  

- 🎵 Play standard MIDI files / 播放标准 MIDI 文件  
- 🎹 Piano keyboard visualization / 钢琴键盘可视化显示  
- 🎼 Multi-track support with different colors / 多音轨支持，不同音轨使用不同颜色  
- ⏱️ Real-time falling notes animation / 实时显示音符下落动画  
- 🔈 Supports selecting MIDI output device / 支持选择 MIDI 输出设备  
- 🎶 Auto-detects note range and adjusts display / 自动检测乐曲音符范围并调整显示  
- 🎻 Displays instrument names and track info / 显示乐器名称和曲目信息  

## Requirements / 系统要求  

- Python 3.6+  
- Terminal with ANSI color support / 支持 ANSI 颜色的终端  

## Installation / 安装依赖  

```bash
pip install mido colorama
```  

## Usage / 使用方法  

1. Run the program:  
```bash
python midi_player.py
```  

2. Enter MIDI file path / 输入 MIDI 文件路径  

3. Select MIDI output device (optional) / 选择 MIDI 输出设备（可选）  

4. The program will start playing with visualization / 程序将开始播放 MIDI 文件并显示可视化效果  

## Keyboard Controls / 键盘控制  

- `Ctrl+C` - Stop playback / 停止播放  

## Technical Details / 技术细节  

- Uses `mido` library for MIDI processing / 使用 `mido` 库处理 MIDI 文件  
- Multi-threaded playback and display / 多线程处理音符播放和显示  
- Auto-adjusts display range for different songs / 自动调整显示范围以适应不同乐曲  
- Supports 128 standard MIDI instruments / 支持 128 种标准 MIDI 乐器  

## Known Limitations / 已知限制  

- Only supports standard MIDI files (.mid) / 仅支持标准 MIDI 文件格式 (.mid)  
- Visualization may not work properly in some terminals / 可视化效果在部分终端中可能显示不正常  
- Complex MIDI files may have performance issues / 复杂的 MIDI 文件可能会有性能问题  

## License / 许可证  

GTL 3.0 License / GTL 3.0 许可证
