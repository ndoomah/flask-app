import json
import os
from threading import Thread, Event

from flask import Flask, render_template
from flask_socketio import SocketIO
from xml.dom import minidom

thread = Thread()
thread_stop_event = Event()
import pymongo
from geopy.geocoders import Nominatim

DB_URI = 'mongodb+srv://fyp_admin:fyp_pwd@cluster0-oov30.mongodb.net/test?retryWrites=true'


def getDiseaseInfo():
    # parse an xml file by name
    mydoc = minidom.parse('./static/disease.xml')

    items = mydoc.getElementsByTagName('disease')
    disease_result = []
    for elem in items:
        id = elem.attributes['id'].value
        im = elem.getElementsByTagName('image')[0].childNodes[0].data
        ov = elem.getElementsByTagName('overview')[0].childNodes[0].data
        ca = elem.getElementsByTagName('causes')[0].childNodes[0].data
        sy = elem.getElementsByTagName('symptoms')[0].childNodes[0].data
        tr = elem.getElementsByTagName('treatment')[0].childNodes[0].data
        pr = elem.getElementsByTagName('prevention')[0].childNodes[0].data

        disease_result.append({
            "id": id,
            "image": im,
            "overview": ov,
            "causes": ca,
            "symptoms": sy,
            "treatment": tr,
            "prevention": pr
        })
    return disease_result

def getArticles():
    client = pymongo.MongoClient(DB_URI)
    db = client.test
    output = db.articles_web.find({})
    result = []
    for data in output:
        l = data['link']
        p = data['published']
        t = data['title']
        c = data['text']
        i = data['image']

        result.append({"link": l, "published": p, "title": t, "text": c, "image": i})
    client.close()
    return result

def getLocationCoord(loc):
	geolocator = Nominatim()
	location = geolocator.geocode(loc + " ,Mauritius")
	print((location.latitude, location.longitude))
	long = location.longitude
	lat = location.latitude
	return (long, lat)

class RandomThread(Thread):
    def __init__(self):
        self.delay = 1
        super(RandomThread, self).__init__()
        #self.process = process
    def getRecent(self):
        client = pymongo.MongoClient(DB_URI)
        db = client.test
        with db.watch() as stream:
            for document in stream:
                print(document)
                doc = document['fullDocument']
                try:
                    loc = doc['location']
                    print(loc)
                    if loc != "Not found":
                        long, lat = getLocationCoord(loc)
                    else:
                        print("Failed to get location coordinates due to no location text")
                except:
                    lat = doc['latitude']
                    long = doc['longitude']

                disease = doc['diseasetype']
                time = doc['date']
                loc = doc['location']


                socketio.emit('newdata', {'lat': lat, 'lng': long, 'dis': disease, 'time': time, 'location':loc}, namespace='/test')


    def listen(self):
        client = pymongo.MongoClient(DB_URI)
        db = client.test
        with db.watch() as stream:
            for document in stream:
                print(document)
                doc = document['fullDocument']

                try:
                    disease = doc['diseasetype']
                    loc = doc['location']
                    date = doc['date']

                    socketio.emit('notif', {'dis': disease, 'time': date, 'location':loc}, namespace='/notification')
                except:
                    print("invalid data")
    def run(self):
        '''if self.process == "notif":
            self.listen()
        if self.process == "map":
            self.getRecent()'''
        self.getRecent()


PROJECT_PATH = os.path.dirname(os.path.realpath(__file__))

#app = Flask(__name__)
app = Flask(__name__,
    template_folder=os.path.join(PROJECT_PATH, 'templates'),
    static_folder=os.path.join(PROJECT_PATH, 'static')
)
socketio = SocketIO(app)

@app.route("/")
def index():
    return render_template('index.html', result=getArticles(), disease=getDiseaseInfo())

@app.route("/map_realtime")
def map_realtime():
    return render_template('map.html')

@app.route("/predict")
def predict():
    return render_template('predict.html')


@socketio.on('connect', namespace='/test')
def test_connect():
    # need visibility of the global thread object
    global thread
    print('Client connected')
    #socketio.emit('newdata', {'lat': '-20.2233014','lng': '57.5382649'}, namespace='/test')
    #Start the random number generator thread only if the thread has not been started before.
    if not thread.isAlive():
        print("Starting Thread")
        thread = RandomThread()
        thread.start()

'''@socketio.on('connect', namespace='/notification')
def notif_connect():
    # need visibility of the global thread object
    global thread
    print('Client connected')

    if not thread.isAlive():
        print("Starting Notification Thread")
        thread = RandomThread('notif')
        thread.start()'''

'''@socketio.on('my_event', namespace='/test')
def test_message():
    socketio.emit('newdata', {'lat': '-20.2233014','lng': '57.5382649'}, namespace='/test')'''

if __name__ == "__main__":
    port = int(os.environ.get('PORT'))
    socketio.run(app, host='0.0.0.0', port=port, resource="socket.io", policy_server=False)
    #socketio.run(app)
    #app.run()
