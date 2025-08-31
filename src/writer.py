import os
import csv
from typing import List
from dataclasses import asdict

from models import Review


class ReviewWriter:
    """Class untuk menulis data review ke file CSV"""
    
    def __init__(self, output_dir: str = "data", output_filename: str = "reviews.csv"):
        self.output_dir = output_dir
        self.output_filename = output_filename
        self.output_path = os.path.join(self.output_dir, self.output_filename)
        self.header_written = False

    def write_csv(self, reviews: List[Review]) -> str:
        """Menulis semua review ke file CSV baru"""
        os.makedirs(self.output_dir, exist_ok=True)
        
        with open(self.output_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["author_name", "rating", "published_at", "text", "author_image_url"])
            writer.writeheader()
            for review in reviews:
                writer.writerow(asdict(review))
        
        self.header_written = True
        return self.output_path

    def append_to_csv(self, reviews: List[Review]) -> str:
        """Append review baru ke file CSV yang sudah ada"""
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Check if file exists and has header
        file_exists = os.path.exists(self.output_path)
        
        with open(self.output_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["author_name", "rating", "published_at", "text", "author_image_url"])
            
            # Write header only if file doesn't exist or header not written yet
            if not file_exists or not self.header_written:
                writer.writeheader()
                self.header_written = True
            
            # Write the new reviews
            for review in reviews:
                writer.writerow(asdict(review))
        
        return self.output_path 