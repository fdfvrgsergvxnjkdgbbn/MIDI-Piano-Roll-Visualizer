import mido
import time
import threading
import os
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import queue
import math
import colorama
colorama.init()

# 颜色定义
COLOR_RESET = '\033[0m'
COLOR_CLEAR = '\033[2J\033[H'
COLOR_BG_WHITE = '\033[47m'
TRACK_COLORS = [
    '\033[41m',  # 红
    '\033[42m',  # 绿
    '\033[43m',  # 黄
    '\033[44m',  # 蓝
    '\033[45m',  # 紫
    '\033[46m',  # 青
]

# 音符名称
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


@dataclass
class NoteEvent:
    note: int
    velocity: int
    start_time: float
    track: int
    duration: float
    end_time: float = 0


class MIDIPlayer:
    def __init__(self):
        self.midi_file: Optional[mido.MidiFile] = None
        self.output: Optional[mido.ports.BaseOutput] = None
        self.active_notes: Dict[int, List[NoteEvent]] = defaultdict(list)
        self.note_queue: queue.Queue = queue.Queue()
        self.playing: bool = False
        self.start_time: float = 0
        self.min_note: int = 48  # C3
        self.max_note: int = 84  # C6
        self.track_info: Dict[int, Dict] = {}
        self.instruments: Dict[str, int] = defaultdict(int)
        self.tempo: int = 500000  # 默认120bpm
        self.ticks_per_beat: int = 480
        self.note_pos_map: Dict[int, int] = {}
        self.keyboard_positions: List[Tuple[int, str]] = []
        self.display_width: int = 0
        # 设置竖线高度为40
        self.display_height: int = 40
        # 设置最小音符宽度为6个8度
        min_note = 12 * 6 + 48  # C3起，6个8度
        # 统计乐曲实际包含的音符范围
        midi_min_note = 127
        midi_max_note = 0
        if self.midi_file:
            for track in self.midi_file.tracks:
                for msg in track:
                    if msg.type == 'note_on' and msg.velocity > 0:
                        midi_min_note = min(midi_min_note, msg.note)
                        midi_max_note = max(midi_max_note, msg.note)
        # 计算显示范围，居中显示，超出自动扩展
        if midi_min_note <= midi_max_note:
            midi_range = midi_max_note - midi_min_note + 1
            min_range = min_note - 48
            if midi_range < min_range:
                pad = (min_range - midi_range) // 2
                self.min_note = max(0, midi_min_note - pad)
                self.max_note = min(127, midi_max_note + pad + (min_range - midi_range) % 2)
            else:
                self.min_note = midi_min_note
                self.max_note = midi_max_note
        else:
            self.min_note = 48
            self.max_note = min_note
        self._init_keyboard_layout()

    def _init_keyboard_layout(self):
        """初始化键盘布局，全音空一格，半音不空"""
        pos = 0
        self.keyboard_positions = []
        # 创建完整的键盘布局
        for note in range(self.min_note, self.max_note + 1):
            note_name = NOTE_NAMES[note % 12]
            is_black_key = '#' in note_name

            self.note_pos_map[note] = pos
            self.keyboard_positions.append((pos, note_name))

            if not is_black_key:
                pos += 2  # 全音空一格
            else:
                pos += 2  # 半音不空

        self.display_width = pos + 1

    def clear_screen(self):
        print(COLOR_CLEAR, end='')

    def select_output_port(self):
        ports = mido.get_output_names()
        if not ports:
            print("没有找到可用的MIDI输出设备")
            return None

        print("可用的MIDI输出设备:")
        for i, port in enumerate(ports):
            print(f"{i}: {port}")

        while True:
            try:
                choice = input("请选择设备编号(默认0): ").strip()
                if not choice:
                    choice = 0
                else:
                    choice = int(choice)

                if 0 <= choice < len(ports):
                    return mido.open_output(ports[choice])
                print("无效的选择，请重试")
            except ValueError:
                print("请输入数字")

    def load_midi_file(self, file_path: str):
        try:
            self.midi_file = mido.MidiFile(file_path)
            self.ticks_per_beat = self.midi_file.ticks_per_beat
            self.analyze_midi_file()
            return True
        except Exception as e:
            print(f"加载MIDI文件失败: {e}")
            return False

    def analyze_midi_file(self):
        if not self.midi_file:
            return

        self.track_info = {}
        self.instruments = defaultdict(int)
        all_notes = []

        for i, track in enumerate(self.midi_file.tracks):
            program = 0
            notes_in_track = set()

            for msg in track:
                if msg.type == 'program_change':
                    program = msg.program
                elif msg.type == 'note_on' and msg.velocity > 0:
                    notes_in_track.add(msg.note)
                elif msg.type == 'set_tempo':
                    self.tempo = msg.tempo

            self.track_info[i] = {
                'program': program,
                'note_count': len(notes_in_track)
            }

            instrument_name = self.get_instrument_name(program)
            self.instruments[instrument_name] += 1
            all_notes.extend(notes_in_track)


        if all_notes:
            self.min_note = min(max(0, min(all_notes) - 3), 127)
            self.max_note = max(min(127, max(all_notes) + 3), 0)
            self._init_keyboard_layout()

    def get_instrument_name(self, program: int) -> str:
        instruments = [
            "钢琴", "明亮钢琴", "电钢琴", "酒吧钢琴", "罗德钢琴", "合唱钢琴", "羽管键琴", " clavinet",
            "钢片琴", "钟琴", "音乐盒", "颤音琴", "马林巴", "木琴", "管钟", "大扬琴",
            "电风琴", "拉杆风琴", "摇滚风琴", "教堂风琴", "簧风琴", "手风琴", "口琴", "探戈手风琴",
            "尼龙吉他", "钢弦吉他", "爵士吉他", "清音吉他", "闷音吉他", "过载吉他", "失真吉他", "和声吉他",
            "原声贝斯", "指弹贝斯", "拨片贝斯", "无品贝斯", " slap贝斯1", " slap贝斯2", "合成贝斯1", "合成贝斯2",
            "小提琴", "中提提琴", "大提琴", "低音提琴", "颤音弦乐", "拨奏弦乐", "竖琴", "定音鼓",
            "弦乐合奏1", "弦乐合奏2", "合成弦乐1", "合成弦乐2", "合唱人声", "人声哼唱", "合成人声", "管弦乐打击乐",
            "小号", "长号", "大号", "弱音小号", "法国号", "铜管组", "合成铜管1", "合成铜管2",
            "高音萨克斯", "中音萨克斯", "次中音萨克斯", "上低音萨克斯", "双簧管", "英国管", "巴松管", "单簧管",
            "短笛", "长笛", "竖笛", "排箫", "吹瓶", "尺八", "口哨", "奥卡里那",
            "合成主音1", "合成主音2", "合成主音3", "合成主音4", "合成主音5", "合成主音6", "合成主音7", "合成主音8",
            "合成背景1", "合成背景2", "合成背景3", "合成背景4", "合成背景5", "合成背景6", "合成背景7", "合成背景8",
            "合成效果1", "合成效果2", "合成效果3", "合成效果4", "合成效果5", "合成效果6", "合成效果7", "合成效果8",
            "民族乐器1", "民族乐器2", "民族乐器3", "民族乐器4", "民族乐器5", "民族乐器6", "民族乐器7", "民族乐器8",
            "打击乐1", "打击乐2", "合成鼓", "声音效果", "反转音效", "吉他品噪声", "呼吸噪声", "海浪",
            "鸟鸣", "电话铃", "直升机", "掌声", "枪声"
        ]
        return instruments[program] if program < len(instruments) else f"乐器{program + 1}"

    def display_header(self):
        if not self.midi_file:
            return

        instruments_str = "、".join([f"{count}{name}" for name, count in self.instruments.items()])
        bpm = int(60000000 / self.tempo)
        header = (f"文件名: {os.path.basename(self.midi_file.filename)} "
                  f"音轨数: {len(self.midi_file.tracks)} "
                  f"乐器: {instruments_str} "
                  f"速度: {bpm}BPM")
        print(header[:self.display_width].ljust(self.display_width))

    def display_keyboard(self, block_queue=None):
        print("\033[2;1H\033[K")  # 清屏并将光标移动到左上角
        screen_lines = [[' ' for _ in range(self.display_width)] for _ in range(self.display_height)]
        # 绘制静态的竖线
        for pos, name in self.keyboard_positions:
            for line in range(self.display_height):
                screen_lines[line][pos] = '|'
        # 显示下落方块
        if block_queue:
            for block in block_queue:
                note = block['note']
                track = block['track']
                steps = block['steps']
                if note in self.note_pos_map:
                    pos = self.note_pos_map[note]
                    line = min(steps, self.display_height - 1)
                    color = TRACK_COLORS[track % len(TRACK_COLORS)]
                    screen_lines[line][pos] = f"{color} {COLOR_RESET}"
        # 显示键盘名称（只显示白键名称）
        keyboard_line = [' ' for _ in range(self.display_width)]
        for pos, name in self.keyboard_positions:
            if '#' not in name:
                keyboard_line[pos] = name[0]
        self.clear_screen()
        self.display_header()
        for line in screen_lines:
            print(''.join(line))
        print(''.join(keyboard_line))

    def play_note(self, note: int, velocity: int, duration: float, track: int):
        if not self.output:
            return

        self.output.send(mido.Message('note_on', note=note, velocity=velocity))

        event = NoteEvent(
            note=note,
            velocity=velocity,
            start_time=time.time() - self.start_time,
            track=track,
            duration=duration,
            end_time=time.time() - self.start_time + duration
        )
        self.active_notes[note].append(event)
        self.note_queue.put(event)

    def stop_note(self, note: int):
        if not self.output:
            return

        self.output.send(mido.Message('note_off', note=note))
        if note in self.active_notes and self.active_notes[note]:
            self.active_notes[note].pop(0)

    def play_midi(self):
        if not self.midi_file or not self.output:
            return

        self.playing = True
        self.start_time = time.time()

        display_thread = threading.Thread(target=self.update_display)
        display_thread.daemon = True
        display_thread.start()

        cleanup_thread = threading.Thread(target=self.cleanup_notes)
        cleanup_thread.daemon = True
        cleanup_thread.start()

        # 播放MIDI
        for i, track in enumerate(self.midi_file.tracks):
            if not self.playing:
                break

            playback_time = 0.0
            for msg in track:
                if not self.playing:
                    break

                playback_time += msg.time
                while (time.time() - self.start_time) < (playback_time * self.tempo / (self.ticks_per_beat * 1000000)):
                    time.sleep(0.001)

                if msg.type == 'note_on' and msg.velocity > 0:
                    duration = self.find_note_duration(track, msg)
                    self.play_note(msg.note, msg.velocity, duration, i)
                elif msg.type == 'set_tempo':
                    self.tempo = msg.tempo

        self.playing = False
        display_thread.join()
        cleanup_thread.join()

    def find_note_duration(self, track, note_on_msg) -> float:
        ticks = 0
        for msg in track:
            if (msg.type == 'note_off' or
                (msg.type == 'note_on' and msg.velocity == 0)) and msg.note == note_on_msg.note:
                return msg.time * self.tempo / (self.ticks_per_beat * 1000000)
            ticks += msg.time
        return 0.1  # 默认0.5秒

    def update_display(self):
        while self.playing:
            self.display_keyboard()
            time.sleep(0.1)

    def cleanup_notes(self):
        while self.playing or not self.note_queue.empty():
            try:
                event = self.note_queue.get(timeout=0.1)
                elapsed = (time.time() - self.start_time - event.start_time)

                if elapsed < event.duration:
                    time.sleep(event.duration - elapsed)

                self.stop_note(event.note)
            except queue.Empty:
                continue

    def play_midi_loop(self, midi_path: str, output_port: str = None):
        """主循环，播放MIDI并显示下落方块"""
        self.midi_file = mido.MidiFile(midi_path)
        self.start_time = time.time()
        self.active_notes.clear()
        if output_port:
            self.output = mido.open_output(output_port)
        else:
            self.output = mido.open_output()
        # 预处理所有音符事件
        events = []
        abs_time = 0.0
        tempo = 500000  # 默认初始tempo（微秒/四分音符）
        ticks_per_beat = self.midi_file.ticks_per_beat
        for i, track in enumerate(self.midi_file.tracks):
            abs_time = 0.0
            for msg in track:
                # 时间单位转换：tick -> 秒
                if msg.type == 'set_tempo':
                    tempo = msg.tempo
                abs_time += (msg.time * tempo) / ticks_per_beat / 1_000_000
                if msg.type == 'note_on' and msg.velocity > 0:
                    events.append((abs_time, 'on', msg.note, msg.velocity, i))
                elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
                    events.append((abs_time, 'off', msg.note, 0, i))
        events.sort()
        # 播放主循环
        idx = 0
        total_events = len(events)
        block_queue = []  # [(note, velocity, track, 剩余下落步数)]
        idx = 0
        total_events = len(events)
        # 假设每个方块下落到底需要 N 步
        DROP_STEPS = 5
        while idx < total_events or block_queue:
            now = time.time() - self.start_time
            # 收到到达当前时间的事件，加入方块队列
            while idx < total_events and events[idx][0] <= now:
                etime, etype, note, velocity, track = events[idx]
                if etype == 'on':
                    block_queue.append({'note': note, 'velocity': velocity, 'track': track, 'steps': 0, 'etype': 'on'})
                elif etype == 'off':
                    block_queue.append({'note': note, 'velocity': 0, 'track': track, 'steps': 0, 'etype': 'off'})
                idx += 1
            # 所有方块下落一格
            for block in block_queue:
                block['steps'] += 1
            # 显示方块（每个方块只下落一格竖线）
            self.display_keyboard(block_queue)
            # 检查是否有方块到底
            to_remove = []
            for i, block in enumerate(block_queue):
                if block['steps'] >= self.display_height - 1:
                    note = block['note']
                    velocity = block['velocity']
                    track = block['track']
                    etype = block['etype']
                    if etype == 'on':
                        ne = NoteEvent(note, velocity, now, track, 0.5)
                        self.active_notes[note].append(ne)
                        if self.output:
                            self.output.send(mido.Message('note_on', note=note, velocity=velocity))
                    elif etype == 'off':
                        self.active_notes[note] = [ev for ev in self.active_notes[note] if now - ev.start_time < ev.duration]
                        if self.output:
                            self.output.send(mido.Message('note_off', note=note, velocity=0))
                    to_remove.append(i)
            # 移除已到底的方块
            for i in reversed(to_remove):
                block_queue.pop(i)
            # 移除过期音符
            for note in list(self.active_notes.keys()):
                self.active_notes[note] = [ev for ev in self.active_notes[note] if now - ev.start_time < ev.duration]
                if not self.active_notes[note]:
                    del self.active_notes[note]
            time.sleep(0.05)
        # 关闭所有音符
        if self.output:
            for note in range(self.min_note, self.max_note+1):
                self.output.send(mido.Message('note_off', note=note, velocity=0))
            self.output.close()

    def run(self):
        self.clear_screen()

        file_path = input("请输入MIDI文件路径: ").strip()
        if not self.load_midi_file(file_path):
            return

        self.output = self.select_output_port()
        if not self.output:
            return

        try:
            self.play_midi()
        except KeyboardInterrupt:
            print("\n播放停止")
        finally:
            if self.output:
                self.output.close()


if __name__ == "__main__":
    player = MIDIPlayer()
    print("\033[2J\033[H")
    file_path = input("请输入MIDI文件路径: ").strip()
    ports = mido.get_output_names()
    if not ports:
        print("没有找到可用的MIDI输出设备")
    else:
        print("可用的MIDI输出设备:")
        for i, port in enumerate(ports):
            print(f"{i}: {port}")
        choice = input("请选择设备编号(默认0): ").strip()
        print("\033[?25l\033[2J\033[H")  # 隐藏光标并清屏
        if not choice:
            choice = 0
        else:
            choice = int(choice)
        output_port = ports[choice] if 0 <= choice < len(ports) else ports[0]
        player.play_midi_loop(file_path, output_port)
