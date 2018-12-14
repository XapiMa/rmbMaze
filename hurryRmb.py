# -*- coding: utf-8 -*-
import os
import sys
import time
import socket
import subprocess
import random
import pycreate2 
import csv
import numpy as np
import pandas as pd
import cv2
from contextlib import closing
from sklearn import tree
from sklearn.ensemble import RandomForestClassifier
from datetime import datetime

# タイヤ間の距離23cm

# 時間での管理を諦め、画像での管理に専念したい

RIGHT = -1
LEFT = 1
SPAN = 300


class HurryAPI():
    def __init__(self, sock):
        command = "ls /dev | grep cu.usb"  # ！ここに実行したいコマンドを書く！
        proc = subprocess.Popen(
            command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        stdout_data, stderr_data = proc.communicate()  # 処理実行を待つ
        rmb_port = "/dev/" + stdout_data.decode("utf-8")[:-1]  # 標準出力の確認

        rmb_baudrate = 115200
        self.rmb = pycreate2.Create2(rmb_port, rmb_baudrate)
        
        # 学習時にはTrue 評価時にはFalse
        # self.learnFlag = True
        self.learnFlag = True

        self.nowSpeed = [0,0]
        self.max_speed = 500
        self.name = 'rmb'
        cv2.namedWindow(self.name)
        self.cap = cv2.VideoCapture(0)
        self.cap.set(3, 640)  # カメラの横のサイズ
        self.cap.set(4, 480)  # カメラの縦のサイズ
        self.lineXs = [320 + 100, 320 - 100]
        self.lineYs = [100, 200, 300, 350]
        self.clf = tree.DecisionTreeClassifier(max_depth=6)
        if self.learnFlag == True:
            self.datafile, self.writer = self.openDataFile()
        else:
            self.data_analysis()
        self.sock = sock
        print("init")
        self.rmb_start()

    def rmb_start(self):
        now_status = "pause"
        bufsize = 4096
        self.rmb.start()
        self.rmb.safe()
        print("start")
        while True:
            if self.learnFlag == False:
                    posXs, posYs = self.line_pos(self.lineXs, self.lineYs, 250)
                    key = cv2.waitKey(100) 
            self.check_call()


    def check_call(self):
        posXs, posYs = self.line_pos(self.lineXs, self.lineYs, 250)
        key = cv2.waitKey(1)
        if self.learnFlag == True and now_status != 'pause':
            self.writer.writerow(
                [now_status] + self.nowSpeed + posXs + posYs)
        if self.learnFlag == False:
            # print(posXs, posYs)
            keyText = self.clf.predict(posXs + posYs)
            print(keyText)
            if keyText == "left":
                key = 'a'
            elif keyText == "right":
                key = 'd'
            elif keyText == "straight":
                key = 'w'
        else:
            try:
                key = self.sock.recv(bufsize).decode('utf-8')
            except socket.error:
                pass
        if key == 'a':
            print("go left")
            now_status = "left"
            self.turn_corner(RIGHT)
        elif key == 'd':
            self.turn_corner(LEFT)
            now_status = "right"
        elif key == 'w':
            print("go straight")
            now_status = "straight"
            self.drive_gradually([self.max_speed, self.max_speed])
        elif key == 's':
            print('pause')
            self.drive_gradually([0,0])
        elif key == 'x':
            print('back')
            self.drive_gradually([-500,-500])
        elif key == 'k':
            print('bye')
            cv2.destroyAllWindows()
            if self.learnFlag == True:
                self.datafile.close()
            self.drive_gradually([0,0])
            self.rmb.close()
            exit()
    
    def drive_gradually(self,targetSpeed):
        speedDiff = []
        MAX = self.max_speed
        SPAN = 25
        for (now , target) in zip(self.nowSpeed,targetSpeed):
            if target >MAX:
                target = MAX
            elif target < -MAX:
                target = -MAX
            speedDiff.append(target - now)
        count = max(abs(int(speedDiff[0]//SPAN)),abs(int(speedDiff[1]//SPAN)))
        before=time.time()

        for i in range(count):
            self.nowSpeed[0] += speedDiff[0]//count
            self.nowSpeed[1] += speedDiff[1]//count
            self.rmb.drive_direct(self.nowSpeed[0],self.nowSpeed[1])
            # print("drive",self.nowSpeed[0],self.nowSpeed[1])
            while True:
                after=time.time()
                if(after-before > 0.7): break
                self.check_call()
        self.nowSpeed[0] = targetSpeed[0]
        self.nowSpeed[1] = targetSpeed[1]
        self.rmb.drive_direct(self.nowSpeed[0],self.nowSpeed[1])

    def turn_corner(self, direction):
        # 仮に、ルンバから横に5cmの位置を中心として回転するように設定した
        self.turn(direction, 5)

    def turn(self, direction, distance):
        # distanceは内側のタイヤと回転の中心との距離
        inside = distance // (distance + 23)
        if(direction == RIGHT):
            lSP = 1
            rSP = inside
        elif(direction == LEFT):
            lSP = inside
            rSP = 1
        else:
            lSP = 0
            rSP = 0
        self.drive_gradually([self.max_speed * rSP, self.max_speed * lSP])

    def line_pos(self, Xs, Ys, thd):
        # カメラからgrayのイメージを生成する
        ret, frame = self.cap.read()
        cv2.waitKey(1)
        img = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        image = img.copy()

        yoko = [None for i in range(len(Ys) * 2)]
        tate = [None for i in range(len(Xs) * 2)]
        posXs = []
        posYs = []

        # よこ線認識
        for i in range(len(Xs)):
            tate[i] = image[:, Xs[i]]
        Y_max = image.shape[0]
        Y_mid = Y_max // 2

        for i in range(len(Xs)):
            if max(tate[i][0:Y_mid]) < thd:
                posYs.append(-1)
            else:
                posYs.append(np.argmax(tate[i][0:Y_mid]))

            if np.max(tate[i][Y_mid:Y_max]) < thd:
                # 下にはみ出たということを認識したい．例外として-1を使うと上に出た様になってしまう．
                posYs.append(Y_max + 1)
            else:
                posYs.append(np.argmax(tate[i][Y_mid:Y_max]) + Y_mid)

        # draw line
        for i in range(len(Xs)):
            cv2.line(image, (Xs[i], 0), (Xs[i], Y_max), 100, 2)

            if posYs[i * 2] != -1 and posYs[i * 2] != Y_max + 1:
                cv2.circle(image, (Xs[i], posYs[i * 2]), 10, 100, -1)
            if posYs[i * 2] != -1 and posYs[i * 2] != Y_max + 1:
                cv2.circle(image, (Xs[i], posYs[i * 2 + 1]), 10, 100, -1)

        # たて線認識
        for i in range(len(Ys)):
            yoko[i] = image[Ys[i], :]
        X_max = image.shape[1]
        X_mid = X_max // 2

        for i in range(len(Ys)):
            if max(yoko[i][0:X_mid]) < thd:
                posXs.append(-1)
            else:
                posXs.append(np.argmax(yoko[i][0:X_mid]))

            if max(yoko[i][X_mid:X_max]) < thd:
                # 右端に出たということを認識したい．例外として-1を使うと左に出た様になってしまう．
                posXs.append(X_max + 1)
            else:
                posXs.append(np.argmax(yoko[i][X_mid:X_max]) + X_mid)

        # draw line
        for i in range(len(Ys)):
            cv2.line(image, (0, Ys[i]), (X_max, Ys[i]), 100, 2)

            if posXs[i * 2] != -1 and posXs[i * 2] != X_max + 1:
                cv2.circle(image, (posXs[i * 2], Ys[i]), 10, 100, -1)
            if posXs[i * 2 + 1] != -1 and posXs[i * 2 + 1] != X_max + 1:
                cv2.circle(image, (posXs[i * 2 + 1], Ys[i]), 10, 100, -1)

        cv2.imshow(self.name, image)

        return posXs, posYs


    def openDataFile(self):
        current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        path = os.path.join(current_dir, './data')
        # 指定したパス内の全てのファイルとディレクトリを要素とするリストを返す
        files = os.listdir(path)
        # .ファイルを無視
        files_visible = [f for f in files if f[0] != '.']
        # ディレクトリを無視
        files_visible_files = [
            f for f in files_visible if os.path.isfile(os.path.join(path, f))]
        filename = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        if len(files_visible_files) == 0:
            colname = ['status', 'now_L', 'now_R']
            colname += ['X' + str(i) for i in range(len(self.lineXs) * 2)]
            colname += ['Y' + str(i) for i in range(len(self.lineYs) * 2)]
            with open(os.path.join(path, filename + '.csv'), 'w') as datafile:
                # 改行コード（\n）を指定しておく
                writer = csv.writer(datafile, lineterminator='\n')
                writer.writerow(colname)
            with open(os.path.join(path, filename + '.csv'), 'r') as datafile:
                prevdata = datafile.read()
        else:
            with open(os.path.join(path, files_visible_files[-1]), 'r') as datafile:
                prevdata = datafile.read()

        datafile = open(os.path.join(path, filename + '.csv'), 'w')
        datafile.write(prevdata)

        writer = csv.writer(datafile, lineterminator='\n')  # 改行コード（\n）を指定しておく
        return datafile,  writer

    def data_analysis(self):
        dataset = pd.read_csv("/Users/koba/Documents/class/robotbrain/timeAttack/data/2018-01-19-17:56:36.csv")
        data = dataset[['X' + str(i) for i in range(len(self.lineXs) * 2)] +
                       ['Y' + str(i) for i in range(len(self.lineYs) * 2)]]
        target = dataset["status"]
        target.value_counts()
        self.clf = RandomForestClassifier()
        self.clf = self.clf.fit(data, target)
