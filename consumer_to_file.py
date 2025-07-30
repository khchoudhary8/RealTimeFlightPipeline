from kafka import KafkaConsumer
import json
import os

file_path = 'flight_data.json'
os.makedirs('data', exist_ok=True)

consumer = KafkaConsumer(
    'test-topic',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='flight-group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)
print("Listening for messages to write to file...")

with open('data/data-stream.json', 'a') as f:
    for mes in consumer:
        json.dump(mes.value, f)
        f.write('\n')
        print(f"Wrote message to file: {mes.value}")
        
