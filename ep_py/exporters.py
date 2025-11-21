# -*- coding: utf-8 -*-

import abc
import csv
import json
import logging

class BaseExporter(abc.ABC):
    """Exporter的抽象基类，定义了所有具体Exporter必须实现的接口。"""

    file_extension = ''

    def __init__(self, file_path, fields):
        self.file_path = file_path
        if isinstance(fields[0], dict):
            self.fields = [field['name'] for field in fields]
            self.source_fields = [field.get('source', field['name']) for field in fields]
        else:
            self.fields = fields
            self.source_fields = fields
        self._file = None
        self._writer = None
        if self.file_path:
            self._file = open(self.file_path, 'w', encoding='utf-8', newline='')

    @abc.abstractmethod
    def write_header(self):
        """写入文件头。"""
        pass

    @abc.abstractmethod
    def write_row(self, record):
        """写入单行数据。"""
        pass

    def write_batch(self, records):
        """写入一批数据。"""
        for record in records:
            self.write_row(record)

    def close(self):
        """关闭文件。"""
        if self._file:
            self._file.close()

class CsvExporter(BaseExporter):
    """将数据导出为CSV格式。"""

    file_extension = 'csv'

    def __init__(self, file_path, fields):
        super().__init__(file_path, fields)
        if self._file:
            self._writer = csv.DictWriter(self._file, fieldnames=self.fields)

    def write_header(self):
        if self._writer:
            self._writer.writeheader()
            logging.info(f"CSV header written to {self.file_path}")

    def write_row(self, record):
        if self._writer:
            # 从原始记录中提取数据并映射到目标字段
            row_data = {target_field: record.get(source_field) for target_field, source_field in zip(self.fields, self.source_fields)}
            self._writer.writerow(row_data)

    def write_batch(self, records):
        for record in records:
            self.write_row(record)

class JsonlExporter(BaseExporter):
    """将数据导出为JSON Lines格式。"""

    file_extension = 'jsonl'

    def write_header(self):
        # JSONL格式没有文件头
        if self._file:
            logging.info(f"Starting JSONL export to {self.file_path}")
        pass

    def write_row(self, record):
        if self._file:
            # 从原始记录中提取数据并映射到目标字段
            row_data = {target_field: record.get(source_field) for target_field, source_field in zip(self.fields, self.source_fields)}
            self._file.write(json.dumps(row_data, ensure_ascii=False) + '\n')

    def write_batch(self, records):
        for record in records:
            self.write_row(record)


def get_exporter(config, file_path=None):
    """根据配置返回一个Exporter实例。"""
    output_config = config.get('output', {})
    output_format = output_config.get('format', 'csv').lower()
    fields = output_config.get('fields')

    if not fields:
        raise ValueError("Output fields must be defined in YAML config under 'output.fields'")

    if output_format == 'csv':
        return CsvExporter(file_path, fields)
    elif output_format == 'jsonl':
        return JsonlExporter(file_path, fields)
    # 未来可以在这里添加对Parquet等其他格式的支持
    # elif output_format == 'parquet':
    #     return ParquetExporter(file_path, fields)
    else:
        raise ValueError(f"Unsupported export format: {output_format}")