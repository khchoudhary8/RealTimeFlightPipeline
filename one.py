from opensky_api import OpenSkyApi

# bbox = (min latitude, max latitude, min longitude, max longitude)
api = OpenSkyApi(username='khchoudhary8', password='8409734394Kh$@')
states = api.get_states(bbox=(45.8389, 47.8229, 5.9962, 10.5226))
print(states)
for s in states.states:
    print("(%r, %r, %r, %r)" % (s.longitude, s.latitude, s.baro_altitude, s.velocity))