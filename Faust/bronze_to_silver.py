"""
Bronze to Silver transformation with testable design.
Refactored to enable unit testing without AWS credentials.
"""

import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from schemas.flight_schema import FlightRecord
from Faust.transformation_utils import filter_valid_flights, generate_silver_key


class BronzeToSilverTransformer:
    """
    Transformer that processes bronze layer data into silver layer.

    This class is designed for testability:
    - S3 operations are injected (can be mocked)
    - Pure business logic separated from I/O
    - Easy to test with in-memory data
    """

    def __init__(
        self, s3_client, bucket_name: str, bronze_prefix: str = "bronze/", silver_prefix: str = "silver_flights/"
    ):
        """
        Initialize transformer with S3 client.

        Args:
            s3_client: Boto3 S3 client (or mock for testing)
            bucket_name: S3 bucket name
            bronze_prefix: Prefix for bronze layer files
            silver_prefix: Prefix for silver layer output
        """
        self.s3_client = s3_client
        self.bucket_name = bucket_name
        self.bronze_prefix = bronze_prefix
        self.silver_prefix = silver_prefix

    def list_bronze_keys(self) -> List[str]:
        """
        List all JSON files in bronze prefix.

        Returns:
            List of S3 keys for bronze files
        """
        response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=self.bronze_prefix)
        objects = [obj["Key"] for obj in response.get("Contents", []) if obj["Key"].endswith(".json")]
        return objects

    def read_json_from_s3(self, key: str) -> List[Dict[str, Any]]:
        """
        Read JSON data from S3.

        Args:
            key: S3 object key

        Returns:
            Parsed JSON data (list or dict)
        """
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        content = response["Body"].read().decode("utf-8")
        data = json.loads(content)
        return data if isinstance(data, list) else [data]

    def process_file(self, key: str) -> List[Dict[str, Any]]:
        """
        Process a single bronze file and extract valid flight records.

        Args:
            key: S3 key of bronze file

        Returns:
            List of valid flight dictionaries
        """
        data = self.read_json_from_s3(key)
        valid_flights = filter_valid_flights(data)
        return valid_flights

    def write_to_silver(self, records: List[Dict[str, Any]], timestamp: datetime) -> str:
        """
        Write processed records to silver layer in partitioned S3 location.

        Args:
            records: List of flight record dictionaries
            timestamp: Timestamp for partitioning

        Returns:
            S3 key where data was written
        """
        if not records:
            raise ValueError("Cannot write empty records to silver")

        # Validate with Pydantic schema
        try:
            flight_records = [FlightRecord(**record) for record in records]
            validated_records = [fr.model_dump() for fr in flight_records]
        except Exception as e:
            raise ValueError(f"Schema validation failed: {e}")

        # Create DataFrame
        df = pd.DataFrame(validated_records)

        # Generate S3 key with partitioning
        s3_key = generate_silver_key(self.silver_prefix, timestamp)

        # Write to S3 as JSON (could switch to Parquet)
        self.s3_client.put_object(
            Bucket=self.bucket_name, Key=s3_key, Body=df.to_json(orient="records").encode("utf-8")
        )

        return s3_key

    def transform_all(self) -> Dict[str, Any]:
        """
        Run full bronze to silver transformation.

        Returns:
            Dictionary with transformation results
        """
        keys = self.list_bronze_keys()
        all_records = []
        processed_files = []
        errors = []

        for key in keys:
            try:
                records = self.process_file(key)
                all_records.extend(records)
                processed_files.append(key)
            except Exception as e:
                errors.append({"key": key, "error": str(e)})

        result = {"keys_processed": len(processed_files), "total_records": len(all_records), "errors": errors}

        if all_records:
            s3_key = self.write_to_silver(all_records, datetime.utcnow())
            result["output_key"] = s3_key
            result["success"] = True
        else:
            if processed_files:
                # We processed files but all had invalid data
                result["success"] = False
                result["error"] = "No valid records found in processed files"
            else:
                # No files to process - this is fine, consider it success
                result["success"] = True

        return result


def transform_bronze_to_silver(
    s3_client, bucket_name: str, bronze_prefix: str = "bronze/", silver_prefix: str = "silver_flights/"
) -> Dict[str, Any]:
    """
    Convenience function for one-off transformation.

    Args:
        s3_client: Boto3 S3 client
        bucket_name: S3 bucket name
        bronze_prefix: Bronze layer prefix
        silver_prefix: Silver layer prefix

    Returns:
        Transformation result dictionary
    """
    transformer = BronzeToSilverTransformer(
        s3_client=s3_client, bucket_name=bucket_name, bronze_prefix=bronze_prefix, silver_prefix=silver_prefix
    )
    return transformer.transform_all()


# For backward compatibility with existing script usage
def main():
    """Legacy main function - kept for compatibility"""
    import boto3
    import os
    from dotenv import load_dotenv

    load_dotenv()

    s3 = boto3.client(
        "s3",
        region_name="ap-south-1",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    result = transform_bronze_to_silver(
        s3_client=s3,
        bucket_name="realtimeflightstreamingbuckett",
        bronze_prefix="bronze/",
        silver_prefix="silver_flights/",
    )

    if result["success"]:
        print(f"✅ Transformation complete: {result['total_records']} records")
        print(f"📁 Output: {result['output_key']}")
    else:
        print(f"❌ Transformation failed: {result.get('error')}")


if __name__ == "__main__":
    main()
