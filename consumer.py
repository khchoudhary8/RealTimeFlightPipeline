from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'test-topic',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='flight-group',
    value_deserializer= lambda x: (x.decode('utf-8'))
)

print("Listening for messages...")

for message in consumer:
    print(f"Received message: {message.value}")
    