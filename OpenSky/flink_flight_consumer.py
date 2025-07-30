# import datetime
# import json
# import os
# from pyflink.datastream import StreamExecutionEnvironment
# from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer
# from pyflink.common.serialization import SimpleStringSchema, Encoder
# from pyflink.datastream.connectors.file_system import StreamingFileSink, OutputFileConfig
# from pyflink.common.typeinfo import Types
# from pyflink.common.watermark_strategy import WatermarkStrategy

# # Set JAVA_HOME for PyFlink
# os.environ['JAVA_HOME'] = r"C:\Program Files\Java\jdk-17"

# # Create Flink execution environment
# env = StreamExecutionEnvironment.get_execution_environment()
# env.set_parallelism(1)

# # Add JAR files from environment variable or local files
# jar_files = []
# if 'FLINK_JARS' in os.environ:
#     jar_files = os.environ['FLINK_JARS'].split(',')
#     print(f"✅ Using JAR files from environment: {len(jar_files)} files")
# else:
#     # Fallback to local JAR files
#     jar_dir = os.path.join(os.path.dirname(__file__), '..', 'env', 'Lib', 'site-packages', 'pyflink', 'lib')
#     if os.path.exists(jar_dir):
#         for jar_file in os.listdir(jar_dir):
#             if jar_file.endswith('.jar'):
#                 jar_path = os.path.join(jar_dir, jar_file)
#                 jar_files.append(f"file://{os.path.abspath(jar_path)}")
    
#     # Add Kafka connector JAR
#     kafka_jar = os.path.join(os.path.dirname(__file__), '..', 'flink-connector-kafka-4.0.0-2.0.jar')
#     if os.path.exists(kafka_jar):
#         jar_files.append(f"file://{os.path.abspath(kafka_jar)}")
#         print(f"✅ Added Kafka connector JAR: {kafka_jar}")

# if jar_files:
#     env.add_jars(*jar_files)
#     print(f"✅ Added {len(jar_files)} JAR files to Flink environment")
# else:
#     print("❌ No JAR files found")

# # Use the newer KafkaSource API
# kafka_source = KafkaSource.builder() \
#     .set_bootstrap_servers('localhost:9092') \
#     .set_topics('realtime-flights') \
#     .set_group_id('flink-flight-group') \
#     .set_starting_offsets(KafkaOffsetsInitializer.latest()) \
#     .set_value_only_deserializer(SimpleStringSchema()) \
#     .build()

# # Add the source to the environment using the new API
# ds = env.from_source(
#     source=kafka_source,
#     watermark_strategy=WatermarkStrategy.no_watermarks(),
#     source_name="Kafka Source"
# )

# # Function to enrich the incoming JSON message with a timestamp
# def enrich_with_timestamp(msg):
#     try:
#         record = json.loads(msg)
#         record['processed_at'] = datetime.datetime.utcnow().isoformat()
#         return json.dumps(record)
#     except json.JSONDecodeError:
#         # Handle cases where the message is not valid JSON
#         return json.dumps({
#             "error": "Invalid JSON",
#             "original_message": msg,
#             "processed_at": datetime.datetime.utcnow().isoformat()
#         })

# # Enrich the data stream
# enriched_ds = ds.map(enrich_with_timestamp, output_type=Types.STRING())

# # Configure file sink for local output
# output_path = 'bronze_flights'
# output_file_config = OutputFileConfig.builder() \
#     .with_part_prefix("flights") \
#     .with_part_suffix(".json") \
#     .build()

# # Create the file sink
# file_sink = StreamingFileSink.for_row_format(
#     base_path=output_path,
#     encoder=Encoder.simple_string_encoder()
# ).with_output_file_config(output_file_config).build()

# # Add the sink to the data stream
# enriched_ds.add_sink(file_sink)

# # Print the stream to the console for debugging
# enriched_ds.print()

# print("🚀 Starting PyFlink Kafka consumer...")
# print("✅ Configuration:")
# print(f"   - Kafka topic: realtime-flights")
# print(f"   - Bootstrap servers: localhost:9092")
# print(f"   - Consumer group: flink-flight-group")
# print(f"   - Auto offset reset: latest (only new messages)")
# print(f"   - Output path: {output_path}")

# # Execute the Flink job
# env.execute("Kafka to Local File Bronze Ingestion (PyFlink 2.0.0)")
