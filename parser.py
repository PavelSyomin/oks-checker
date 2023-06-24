import sys
import datetime
import pathlib
import pickle
import re

import fuzzysearch
import numpy as np
import pandas as pd
import PyPDF2


class Parser():
    MAX_DIST = 10

    def __init__(self, use_cache=True):
        self._file_path = None
        self._cache = None
        self._use_cache = use_cache

    def load_pdf(self, file_path):
        self._text = {}
        self._data = {}
        self._parsed = {}

        cached = self._load_from_cache(file_path)
        if cached:
            return None

        try:
            with open(file_path, "rb") as f:
                pdf_file = PyPDF2.PdfFileReader(f)
                print(f"File {file_path} loaded")
                self._npages = pdf_file.numPages
                print(f"PDF contatins {self._npages} pages")
                for page_number in range(self._npages):
                    page = pdf_file.getPage(page_number)
                    text = " ".join(page.extractText().splitlines())
                    self._text[page_number + 1] = text
                print(f"Text loaded")
        except:
            print(f"Unable to read text from PDF file {file_path}")

        self._data["file_path"] = file_path
        self._save_to_cache(file_path)

    def parse(self, searches):
        result = []
        print(f"Search list contains {len(searches)} items")

        for search in searches:
            for n_page, page_text in self._text.items():
                print(f"Checking page #{n_page}")
                matches = fuzzysearch.find_near_matches(
                    search.lower(), page_text.lower(), max_l_dist=self.MAX_DIST)
                print(f"Found {len(matches)} matches")
                for match in matches:
                    if match.dist == 0:
                        class_ = "perfect"
                    elif match.dist < 5:
                        class_ = "small"
                    else:
                        class_ = "big"
                    result_item = {
                        "search": search,
                        "match": match.matched,
                        "distance": match.dist,
                        "start": match.start,
                        "end": match.end,
                        "page": n_page,
                        "class": class_,
                    }
                    result.append(result_item)
        print("Check completed")

        self._parsed = result

    def _build_cache_file_path(self, file_path):
        cache_path = pathlib.Path("cache")
        file_path = file_path.replace(".pdf", ".dump")
        pdf_file =  pathlib.Path(file_path)
        cache_file = cache_path / pdf_file.name

        return cache_file

    def _load_from_cache(self, file_path):
        if not self._use_cache:
            return None

        cache_file = self._build_cache_file_path(file_path)
        if cache_file.exists():
            try:
                with open(cache_file, "rb") as f:
                    data = pickle.load(f)
                    self._text = data["text"]
            except:
                print(f"Cannot load cache")
                return None

            print(f"Data for file {file_path} loaded from cache")
            return True

        return False

    def _save_to_cache(self, file_path):
        cache_file = self._build_cache_file_path(file_path)

        try:
            with open(cache_file, "wb") as f:
                data = {
                    "text": self._text
                }
                pickle.dump(data, f)
        except Exception as e:
            print(f"Cannot save to cache")
            print(e)

    def get_result(self):
        if self._parsed is not None and self._text:
            total_count = len(self._parsed)
            perfect = len([item for item in self._parsed if item["distance"] == 0])
            small_errors_count = len([item for item in self._parsed if item["distance"] < 5])
            big_errors_count = total_count - small_errors_count - perfect

            return {
                "matches": self._parsed,
                "text": self._text,
                "counts": {
                    "total": total_count,
                    "perfect": perfect,
                    "small_errors": small_errors_count,
                    "big_errors": big_errors_count,
                },
            }

        return {"status": "Error"}
