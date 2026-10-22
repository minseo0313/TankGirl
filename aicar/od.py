# OpenCV Object Detection                                                    <v14.py>
#
# 인식 가능한 물체 리스트
#
# 사람, 자전거, 자동차, 오토바이, 비행기, 버스, 기차, 트럭, 보트, 신호등
# 소화전, 거리 표지판, 정지 신호, 주차 미터기, 벤치, 새, 고양이, 개, 말
# 양, 소, 코끼리, 곰, 얼룩말, 기린, 모자, 배낭, 우산, 신발, 안경
# 핸드백, 넥타이, 여행가방, 프리스비, 스키, 스노우보드, 스포츠공, 연, 야구방망이
# 야구 글러브, 스케이트보드, 서핑보드, 테니스 라켓, 병, 접시, 와인잔, 컵
# 포크, 나이프, 스푼, 그릇, 바나나, 사과, 샌드위치, 오렌지, 브로콜리, 당근, 핫도그
# 피자, 도넛, 케이크, 의자, 소파, 화분, 침대, 거울, 식탁, 창문
# 책상, 화장실, 문, TV, 노트북, 마우스, 리모컨, 키보드, 휴대폰, 전자레인지
# 오븐, 토스터, 싱크대, 냉장고, 믹서기, 책, 시계, 꽃병, 가위, 테디베어
# 헤어드라이어, 칫솔, 머리빗
#
import cv2

thres = 0.5 # Threshold Detect

cap = cv2.VideoCapture(0,cv2.CAP_V4L)       # 카메라 객체 생성
cap.set(3,640)
cap.set(4,480)

configPath = 'od_ssd.pbtxt'
weightsPath = 'od_graph.pb'
classFile = 'od_coco.names'

with open(classFile,'rt') as f:
    classNames = f.read().rstrip('\n').split('\n')

net = cv2.dnn_DetectionModel(weightsPath,configPath)
net.setInputSize(320,320)               # 이미지의 크기를 320x320으로 설정
net.setInputScale(1.0/127.5)            # 데이터를 127.5로 나누어 정규화
net.setInputMean((127.5, 127.5, 127.5)) # 이미지에서 빼야 할 평균 값을 설정
net.setInputSwapRB(True)                # 이미지의 색상 채널 순서를 변경하는 옵션

while True:
    _, img = cap.read()
    classIds, confs, bbox = net.detect(img, confThreshold=thres)
    #print(classIds,bbox)

    if len(classIds) != 0:
        for classId, confidence, box in zip(classIds.flatten(),confs.flatten(),bbox): 
            cv2.rectangle(img,box,color=(0,255,0),thickness=2)
            cv2.putText(img,classNames[classId-1],(box[0]+10,box[1]+15),cv2.FONT_HERSHEY_PLAIN,1,(0,255,0),1)
            cv2.putText(img,f'{confidence*100:.2f}',(box[0]+10, box[1]+30),cv2.FONT_HERSHEY_PLAIN,1,(0,255,0),1)

    cv2.imshow("Out", img)
    key = cv2.waitKey(1)    

    if key == ord(' ') or key == ord('x') or key == ord('X') or key == 27: # SPACE, 'x', 'X', ESC
        break
cv2.destroyAllWindows()                              # 열려 있는 모든 윈도우를 닫기
#############################################################################################
