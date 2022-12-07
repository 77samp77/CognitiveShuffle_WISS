import tkinter as tk
import webbrowser
import threading
import random
import urllib
from urllib.parse import quote
import winsound
import time
import math
import datetime
import pytz
import csv

# NCMBの各種キー (セキュリティ対策のため伏字)
app_apiKey = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
app_cliKey = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
ncmb = None

def prepare_NCMB():
    global ncmb
    # DBの読み込み
    from NCMB.Client import NCMB
    ncmb = NCMB(app_apiKey, app_cliKey)

# model = None
#
# def prepare_vector():
#     global model
#     # エンティティベクトルの読み込み
#     import gensim
#     from gensim.models import KeyedVectors
#     model = gensim.models.word2vec.KeyedVectors.load_word2vec_format("entity_vector/entity_vector.model.bin", binary=True)

fileName_toRead = "word_data.csv"
word_data = []

def prepare_wordData():
    global word_data
    # 単語データの読み込み
    csv_file = open(fileName_toRead, "r", encoding="Shift-JIS")
    f = csv.reader(csv_file)
    next(f)
    for row in f: word_data.append(row[0])

ready_to_logIn = False

def prepare():
    global ready_to_logIn

    prepare_NCMB()
    # prepare_vector()
    prepare_wordData()
    ready_to_logIn = True

userID = ""
apiKey = "未設定"
REMAIN = 1800

def wait():
    while not loggedIn:
        if want_to_logIn:
            if not ready_to_logIn:
                set_message("しばらくお待ちください…", 0)
                time.sleep(1)
            else:
                progress()
                return
        else: time.sleep(1)


timer_start_flag = False
timer_quitting_flag = False
timer_remain = REMAIN


def click_close():
    if can_readAloud: cancelRead()
    if loggedIn: sendData(3)
    time.sleep(0.5)
    app.root.destroy()

def sendData(state):
    toNCMB_timeStamp = str(datetime.datetime.now(pytz.timezone('Asia/Tokyo')))
    toNCMB_state = "ログイン"
    if state == 1: toNCMB_state = "読み上げ開始"
    if state == 2: toNCMB_state = "読み上げ終了"
    if state == 3: toNCMB_state = "ログアウト"

    obj = ncmb.Object('Test_UserData')
    obj.set(
        'AttendID', userID
    ).set(
        'TimeStamp', toNCMB_timeStamp
    ).set(
        'State', toNCMB_state
    )
    obj.save()

toCSVName_timeStamp = ""
toCSV_timeStamp = []
toCSV_elapsedTime = []
toCSV_word = []

def writeCSV():
    saveName = userID + "__" + toCSVName_timeStamp

    with open(f'log/{saveName}.csv', 'w', newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ユーザID:", userID])
        writer.writerow([""])
        writer.writerow(["タイムスタンプ", "経過時間", "単語"])
        for i in range(len(toCSV_timeStamp)):
            writer.writerow([toCSV_timeStamp[i], toCSV_elapsedTime[i], toCSV_word[i]])

    toCSV_timeStamp.clear()
    toCSV_elapsedTime.clear()
    toCSV_word.clear()

def cancelRead():
    global timer_start_flag
    global count_start_flag
    global choose_start_flag
    global can_readAloud

    timer_start_flag = False
    count_start_flag = False
    choose_start_flag = False
    can_readAloud = False

    writeCSV()
    sendData(2)

def time2ms(time):
    min = math.floor(time / 60)
    sec = time % 60
    return str(min).zfill(2) + ":" + str(sec).zfill(2)

# タイマー
def timer():
    global timer_quitting_flag
    global timer_remain

    while not timer_quitting_flag:
        if timer_start_flag:
            set_message_time("残り... " + time2ms(timer_remain))

            timer_remain -= 1
            time.sleep(1)
            if timer_remain == 0:
                set_message_time("時間終了")
                cancelRead()
                switch_readButton_tex("30")
        else: time.sleep(1)

# タイマーの開始
def start_timer():
    global timer_start_flag
    global timer_remain

    timer_remain = REMAIN
    timer_start_flag = True

can_readAloud = False

# 音声の再生(=読み上げ)
def readAloud():
    if can_readAloud:
        global toCSV_timeStamp
        global toCSV_elapsedTime
        global toCSV_word

        toCSV_timeStamp.append(str(datetime.datetime.now(pytz.timezone('Asia/Tokyo'))))
        elapsedTime = time2ms(REMAIN - timer_remain)
        toCSV_elapsedTime.append(elapsedTime)
        toCSV_word.append(word_previous)
        set_message(word_previous, 2)

        winsound.PlaySound("audio.wav", winsound.SND_FILENAME)
        start_read()


# 10カウント用の変数定義
count_start_flag = False
count_quitting_flag = False
count = 10

# count_start_flagがTrueになったら10数える
def secCount():
    global count_start_flag
    global count_quitting_flag
    # global start_count
    global count

    while not count_quitting_flag:
        if count_start_flag:
            count -= 10
            time.sleep(10)
            if count == 0:
                count_start_flag = False
            if not choose_start_flag: readAloud()
        else: time.sleep(1)

# カウント開始
def start_count():
    global count_start_flag
    global count

    if count_start_flag: return
    count = 10
    count_start_flag = True

# APIキーの検証
def verify_API(_apiKey):
    global apiKey

    if _apiKey == "":
        set_message("APIキーを入力してください", 1)
        return False

    if _apiKey == "未入力":
        set_message("入力されたAPIキーは存在しません", 1)
        return False

    if _apiKey == apiKey:
        return True

    try:
        url = f'https://api.su-shiki.com/v2/api?key={_apiKey}'
        urllib.request.urlopen(url) # アクセス可能か調べる
        apiKey=_apiKey
        app.label_ID_API["text"] = "ID: " + userID + "\nAPIキー: " + apiKey
        return True
    except Exception as e:
        if str(e) == "HTTP Error 403: Forbidden": set_message("入力されたAPIキーは存在しません", 1)
        elif str(e) == "<urlopen error [Errno 11001] getaddrinfo failed>": set_message("ネットワークにアクセスできません", 1)
        else:
            set_message(str(e), 1)
        switch_readButton_tex("21")
        return False

## 単語選出関連の変数定義
choose_quitting_flag = False
choose_start_flag = False
choose_word_num = 0
choose_word_len = 50
word_previous = ""

# 音声合成、wavファイルの保存
def generate_wav(_word):
    global choose_start_flag
    global count_start_flag

    url = f'https://api.su-shiki.com/v2/voicevox/audio/?key={apiKey}&speaker=31&pitch=0&intonationScale=1&speed=1&text={_word}'
    data = urllib.request.urlopen(url)
    f = open('audio.wav', 'wb')
    f.write(data.read())
    f.close()
    choose_start_flag = False

    if not count_start_flag: readAloud()

nums_word_read = []

# 単語の決定
def decide_word(read_num):
    global word_previous

    word_read = word_data[read_num]
    word_previous = word_read

    # 直近既読リストに登録
    nums_word_read.append(read_num)
    # 直近既読リストが単語リストの2/3を超えたら、そのうち最初から2/5を除外
    if len(nums_word_read) > int(len(word_data) * 2 / 3): del nums_word_read[:int(len(nums_word_read) * 2 / 5)]

    generate_wav(quote(word_read))

# 直近既読リストに含まれるかどうか
def alreadyRead(cwn):
    for i in nums_word_read:
        if cwn == i: return True
    return False

# その時点で読み上げるのに適するかどうか
def isSuitToRead(cwn):
    # if model.similarity(word_previous, word_data[cwn]) > 0.2: return False
    if alreadyRead(cwn): return False
    return True

# 単語の選出
def choose():
    global choose_quitting_flag
    global choose_start_flag
    global choose_word_num
    global choose_word_len

    while not choose_quitting_flag:
        if choose_start_flag:
            choose_word_num = random.randrange(len(word_data))
            while not isSuitToRead(choose_word_num):
                choose_word_num += 1
                if choose_word_num >= len(word_data): choose_word_num = 0
                time.sleep(0.5)
            decide_word(choose_word_num)
            choose_word_num = random.randrange(len(word_data))
        else: time.sleep(1)

def start_read():
    global choose_start_flag
    global choose_word_num
    global choose_word_len
    global count_start_flag

    start_count()

    if word_previous == "":
        choose_word_num = random.randrange(0, choose_word_len)
        decide_word(choose_word_num)
    else:
        choose_start_flag = True

# 単語選出はじめ(ボタンが押されたときのみ)
def start_choose():
    global can_readAloud

    can_readAloud = True
    start_timer()
    start_read()

def jump_to_link(url):
    webbrowser.open_new(url)

def Read():
    if choose_start_flag or count_start_flag:
        switch_readButton_tex("21")
        return

    start_choose()
    set_message("", 0)
    switch_readButton_tex("24")
    sendData(1)

def change_page():
    app.label_exp.place(x=-500, y=-500)
    app.label_ID.place(x=-500, y=-500)
    app.entry_ID.place(x=-500, y=-500)
    app.label_API.place(x=-500, y=-500)
    app.entry_API.place(x=-500, y=-500)
    app.label_link_getAPI.place(x=-500, y=-500)
    app.canvas_next.place(x=-500, y=-500)
    app.label_ID_API.place(x=app.label_ID_API_x, y=app.label_ID_API_y)
    app.canvas_read.place(x=app.button_read_x, y=app.button_read_y)
    set_message("こんばんは。", 0)

def verify_ID(_id):
    global userID

    if _id == "":
        set_message("参加IDを入力してください。", 1)
        return False

    try:
        int(_id)
    except:
        set_message("参加IDは1～3桁の算用数字で入力してください。", 1)
        return False

    if len(_id) > 3:
        set_message("参加IDは1～3桁の算用数字で入力してください。", 1)
        return False

    userID = _id
    return True

loggedIn = False

def progress():
    global loggedIn

    sendData(0)
    loggedIn = True
    change_page()

want_to_logIn = False

def press_nextButton(event):
    global want_to_logIn

    if not cursor_in_nextButton: return
    if not verify_ID(app.entry_ID.get()): return
    if not verify_API(app.entry_API.get()): return

    want_to_logIn = True


cursor_in_nextButton = False

def switch_cinB(stat):
    global cursor_in_nextButton
    cursor_in_nextButton = stat

def switch_nextButton_tex(stat):
    #### 0...default　1...hover　2...press
    list_stat = list(stat)

    tex_next = app.tex_nb[int(list_stat[1])]
    tag_prev = "i" + list_stat[0]
    tag_next = "i" + list_stat[1]

    app.canvas_next.delete(tag_prev)
    app.canvas_next.create_image(app.canvas_next_width / 2, app.canvas_next_height / 2, image=tex_next, tag=tag_next)

def press_readButton(event):
    if not cursor_in_readButton: return

    if can_readAloud:
        cancelRead()
        set_message("読み上げを中止しました", 0)
        switch_readButton_tex("51")
    else:
        global toCSVName_timeStamp

        pre_now_0 = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))
        pre_now_1 = str(pre_now_0).split('-')
        pre_now_2 = pre_now_1[2].split(' ')
        pre_now_3 = pre_now_2[1].split(':')
        pre_now_4 = pre_now_3[2].split('.')
        toCSVName_timeStamp = pre_now_1[0] + pre_now_1[1] + pre_now_2[0] + "_" + pre_now_3[0] + pre_now_3[1] + pre_now_4[0] + "_" + pre_now_4[1][0:2]

        Read()

cursor_in_readButton = False

def switch_cirB(stat):
    global cursor_in_readButton
    cursor_in_readButton = stat

def switch_readButton_tex(stat):
    #### 0...x読,default　1...x読,hover　2...x読,press　3...o読,default　4...o読,hover　5...o読,press

    global can_readAloud

    list_stat = list(stat)
    if can_readAloud:
        if stat == "01" or stat == "10" or stat == "12":
            for i in range(2): list_stat[i] = str(int(list_stat[i]) + 3)

    tex_next = app.tex_rb[int(list_stat[1])]
    tag_prev = "i" + list_stat[0]
    tag_next = "i" + list_stat[1]
    tag_prev_txt = "t"
    str_next = app.str_rb[int(list_stat[1])]
    tag_next_txt = "t"
    txt_rb_y_next = app.txt_rb_y[int(list_stat[1])]

    app.canvas_read.delete(tag_prev)
    app.canvas_read.create_image(app.canvas_read_width/2, app.canvas_read_height/2, image=tex_next, tag=tag_next)
    app.canvas_read.delete(tag_prev_txt)
    app.canvas_read.create_text(app.txt_rb_x, txt_rb_y_next, text=str_next, fill=app.bgColor, font=(app.fontName_1, 13), tag=tag_next_txt)

def set_message(message, importance):
    app.canvas_message.delete("t")
    txt_color = app.bgColor
    if importance == 1: txt_color = "#FF0000"
    app.canvas_message.create_text(app.txt_message_x, app.txt_message_y, text=message, fill=txt_color, anchor=tk.W, tag="t")
    if importance != 2: app.canvas_message.delete("time")

def set_message_time(message):
    app.canvas_message.delete("time")
    txt_color = app.bgColor
    app.canvas_message.create_text(app.txt_time_x, app.txt_time_y, text=message, fill=txt_color, anchor=tk.E, tag="time")

## アプリの初期化
class Application():
    def __init__(self):
        ## 色など
        self.fontName_1="UD デジタル 教科書体 N-R"
        self.fontName_2="UD デジタル 教科書体 N-B"
        self.fgColor_1 = "#F6F5F9"
        self.fgColor_2 = "#FFF2CC"
        self.bgColor = "#504075"

        # ウィンドウ定義
        self.root = tk.Tk()
        self.root.title(u"CognitiveShuffle")
        self.root.geometry("450x300")
        self.root.configure(bg=self.bgColor)
        self.root.resizable(width=False, height=False)
        self.root.update_idletasks()
        win_width = self.root.winfo_width()
        win_height = self.root.winfo_height()

        ## Label(参加IDとAPIキーを入力してね)
        label_exp_x = 30
        label_exp_y = 40
        self.label_exp = tk.Label(self.root, text="● WISS2022の参加IDと、\n　 WEB版VOICEVOXのAPIキーを入力してください。", justify="left", foreground=self.fgColor_1, bg=self.bgColor, font=(self.fontName_1, 13))
        self.label_exp.place(x=label_exp_x, y=label_exp_y)

        ## Input(参加ID入力)
        label_ID_x = win_width / 2 - 110
        label_ID_y = win_height / 2 - 30
        self.label_ID = tk.Label(self.root, text="参加ID:", foreground=self.fgColor_1, bg=self.bgColor,
                                  font=(self.fontName_1, 13))
        self.label_ID.place(x=label_ID_x, y=label_ID_y)

        entry_ID_x = label_ID_x + 80
        entry_ID_y = label_ID_y + 2
        self.entry_ID = tk.Entry(self.root, width=20)
        self.entry_ID.place(x=entry_ID_x, y=entry_ID_y)

        ## Input(APIキー入力)
        label_API_x = label_ID_x
        label_API_y = label_ID_y + 45
        self.label_API = tk.Label(self.root, text="APIキー:", foreground=self.fgColor_1, bg=self.bgColor, font=(self.fontName_1, 13))
        self.label_API.place(x=label_API_x, y=label_API_y)

        entry_API_x = label_API_x + 80
        entry_API_y = label_API_y + 2
        self.entry_API = tk.Entry(self.root, width=20)
        self.entry_API.place(x=entry_API_x, y=entry_API_y)

        ### (次ボタン周りの変数)
        #### 0...default　1...hover　2...press

        self.tex_nb = []
        self.tex_nb.append(tk.PhotoImage(file="./img/RightButton/Default.png"))
        self.tex_nb.append(tk.PhotoImage(file="./img/RightButton/Hover.png"))
        self.tex_nb.append(tk.PhotoImage(file="./img/RightButton/Press.png"))

        ## Button 「→」
        self.canvas_next = tk.Canvas(self.root, bg=self.bgColor, highlightthickness=0)
        button_next_width = 50
        button_next_height = 54
        button_next_x = win_width - button_next_width - 35
        button_next_y = win_height - button_next_height - 40
        self.canvas_next.place(x=button_next_x, y=button_next_y, width=button_next_width, height=button_next_height)
        self.button_next_tex = self.tex_nb[0]
        self.root.update_idletasks()
        self.canvas_next_width = self.canvas_next.winfo_width()
        self.canvas_next_height = self.canvas_next.winfo_height()
        self.canvas_next.create_image(self.canvas_next_width / 2, self.canvas_next_height / 2,
                                      image=self.button_next_tex, tag="i0")

        self.canvas_next.bind("<ButtonRelease-1>", press_nextButton)
        self.canvas_next.bind("<Enter>", lambda e: switch_cinB(True), "+")
        self.canvas_next.bind("<Leave>", lambda e: switch_cinB(False), "+")
        self.canvas_next.bind("<Enter>", lambda e: switch_nextButton_tex("01"), "+")
        self.canvas_next.bind("<Leave>", lambda e: switch_nextButton_tex("10"), "+")
        self.canvas_next.bind("<Button-1>", lambda e: switch_nextButton_tex("12"), "+")


        ## Label「ユーザID:~~~~~~」
        self.label_ID_API_x = win_width - 5
        self.label_ID_API_y = 20
        self.text_ID_API = "ID: " + userID + "\nAPIキー: " + apiKey
        self.label_ID_API = tk.Label(self.root, text=self.text_ID_API, justify="right", bg=self.bgColor, foreground=self.fgColor_1)
        self.label_ID_API.place(x=-500, y=-500, anchor=tk.E)

        ## Label (生成フォーム)
        self.label_link_getAPI = tk.Label(self.root, text="(生成はこちらから)", foreground=self.fgColor_1, bg=self.bgColor, font=(self.fontName_1, 10))
        self.label_link_getAPI.bind("<Button-1>", lambda e: jump_to_link("https://su-shiki.com/api/"))
        self.label_link_getAPI.place(x=entry_API_x, y=entry_API_y + 26)

        ### (読み上げ開始ボタン周りの変数)
        #### 0...x読,default　1...x読,hover　2...x読,press　3...o読,default　4...o読,hover　5...o読,press

        self.tex_rb = []
        for i in range(2):
            tmp_stat = "NR"
            if i == 1: tmp_stat = "R"
            self.tex_rb.append(tk.PhotoImage(file="./img/ReadButton/" + tmp_stat + "_Default.png"))
            self.tex_rb.append(tk.PhotoImage(file="./img/ReadButton/" + tmp_stat + "_Hover.png"))
            self.tex_rb.append(tk.PhotoImage(file="./img/ReadButton/" + tmp_stat + "_Press.png"))

        self.str_rb = []
        for i in range(3): self.str_rb.append("読み上げ開始")
        for i in range(3): self.str_rb.append("読み上げ中止")

        self.txt_rb_x = 70
        tyd = 30
        typ = 33
        self.txt_rb_y = []
        for i in range(2):
            for j in range(2): self.txt_rb_y.append(tyd)
            self.txt_rb_y.append(typ)

        ## Button 「読み上げ開始」
        self.canvas_read = tk.Canvas(self.root, bg=self.bgColor, highlightthickness=0)
        button_read_width = 140
        button_read_height = 60
        self.button_read_x = win_width / 2 - button_read_width / 2
        self.button_read_y = win_height / 2 - button_read_height / 2
        self.canvas_read.place(x=-500, y=-500, width=button_read_width, height=button_read_height)
        self.button_read_tex = self.tex_rb[0]
        self.root.update_idletasks()
        self.canvas_read_width = self.canvas_read.winfo_width()
        self.canvas_read_height = self.canvas_read.winfo_height()
        self.canvas_read.create_image(self.canvas_read_width / 2, self.canvas_read_height / 2, image=self.button_read_tex, tag="i0")
        self.canvas_read.create_text(self.txt_rb_x, self.txt_rb_y[0], text="読み上げ開始", fill=self.bgColor, font=(self.fontName_1, 13), tag="t")

        self.canvas_read.bind("<ButtonRelease-1>", press_readButton)
        self.canvas_read.bind("<Enter>", lambda e: switch_cirB(True), "+")
        self.canvas_read.bind("<Leave>", lambda e: switch_cirB(False), "+")
        self.canvas_read.bind("<Enter>", lambda e: switch_readButton_tex("01"), "+")
        self.canvas_read.bind("<Leave>", lambda e: switch_readButton_tex("10"), "+")
        self.canvas_read.bind("<Button-1>", lambda e: switch_readButton_tex("12"), "+")

        canvas_message_height= 20

        ## Canvas (寝てる人アイコン)
        self.canvas_sleep = tk.Canvas(self.root, bg=self.bgColor, highlightthickness=0)
        canvas_sleep_width = 80
        canvas_sleep_height = 80
        canvas_sleep_x = 0
        canvas_sleep_y = win_height - canvas_sleep_height - canvas_message_height + 20
        self.canvas_sleep.place(x=canvas_sleep_x, y=canvas_sleep_y, width=canvas_sleep_width, height=canvas_sleep_height)
        self.img_sleep = tk.PhotoImage(file="./img/sleep.png")
        self.canvas_sleep.create_image(canvas_sleep_width/2, canvas_sleep_height/2, image=self.img_sleep)

        ## Canvas (メッセージ)
        self.canvas_message = tk.Canvas(self.root, bg=self.fgColor_1, highlightthickness=0)
        canvas_message_width = win_width
        canvas_message_x = 0
        canvas_message_y = win_height - canvas_message_height
        self.canvas_message.place(x=canvas_message_x, y=canvas_message_y, width=canvas_message_width, height=canvas_message_height)
        self.txt_message_x = 5
        self.txt_message_y = canvas_message_height/2
        self.canvas_message.create_text(self.txt_message_x, self.txt_message_y, text="", fill=self.bgColor, anchor=tk.W, tag="t")
        self.txt_time_x = canvas_message_width - 5
        self.txt_time_y = self.txt_message_y


## 単語ベクトルとかNCMBとか事前準備するスレッド
thread0 = threading.Thread(target=prepare)
thread0.start()

## 秒数カウントを行うスレッド
thread1 = threading.Thread(target=secCount)
thread1.start()

## 単語選出、APIでの選定を行うスレッド
thread2 = threading.Thread(target=choose)
thread2.start()

## 制限時間をはかるタイマーのスレッド
thread3 = threading.Thread(target=timer)
thread3.start()

## 事前準備中にログインしようとしてきたときに待機させるスレッド
thread4 = threading.Thread(target=wait)
thread4.start()

# アプリのループ処理
app = Application()
app.root.protocol("WM_DELETE_WINDOW", click_close)
app.root.mainloop()