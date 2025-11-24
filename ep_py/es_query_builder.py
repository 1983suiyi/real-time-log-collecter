import yaml
import os

class ESQueryBuilder:
    def __init__(self, config_path):
        # Construct the absolute path for the configuration file
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        absolute_config_path = os.path.join(project_root, config_path)

        if not os.path.exists(absolute_config_path):
            raise FileNotFoundError(f"Configuration file not found at {absolute_config_path}")

        with open(absolute_config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        default_idx = self.config.get('index_name')
        print(f"ESQueryBuilder loaded. default_index_name={default_idx}")
        self.index_name = self.config.get('index_name')

        self.rule_builders = {
            'range': self._build_range_clause,
            'term': self._build_term_filter_clause,
            'match_phrase': self._build_match_phrase_clause,
            'regexp': self._build_regexp_clause,
            'exists': self._build_exists_clause,
            'terms': self._build_terms_clause,
            'match': self._build_match_clause,
            'multi_match': self._build_multi_match_clause,
            'bool': self._build_bool_clause,
            'not_exists': self._build_not_exists_clause
        }

    def build_query(self, runtime_params=None, template_override=None):
        query_config = self.config.get('query_config', {})
        query_template_str = template_override or query_config.get('query_template')

        if query_template_str:
            # If a query template is defined, use it
            import json
            query_template = query_template_str if isinstance(query_template_str, dict) else json.loads(query_template_str)

            # Apply runtime parameters to the template
            if runtime_params:
                query_template = self._apply_params(query_template, runtime_params)

            # The template itself is the 'query' part
            query = {"query": query_template}

        else:
            # Fallback to rule-based query building
            rules = query_config.get('rules', [])
            query = {"query": {"bool": {"must": [], "filter": [], "must_not": []}}}
            if runtime_params is None:
                runtime_params = {}
            config_params = query_config.get('params', {})

            for rule_name in rules:
                rule_builder = self.rule_builders.get(rule_name)
                if not rule_builder:
                    continue

                rule_params = config_params.get(rule_name, {})
                clause = rule_builder(rule_params, runtime_params)
                if clause:
                    if isinstance(clause, list):
                        for c in clause:
                            context = c.get('context', 'filter')
                            if 'context' in c:
                                del c['context']
                            if context not in query['query']['bool']:
                                query['query']['bool'][context] = []
                            query['query']['bool'][context].append(c)
                    else:
                        context = clause.get('context', 'must')
                        if 'context' in clause:
                            del clause['context']
                        if context not in query['query']['bool']:
                            query['query']['bool'][context] = []
                        query['query']['bool'][context].append(clause)

        source_fields = query_config.get('source_fields', [])
        if source_fields and (source_fields == '*' or source_fields == ['*']):
            query['_source'] = True
        else:
            query['_source'] = source_fields
        query['size'] = query_config.get('size', 1000)

        if 'aggregations' in query_config:
            aggs_config = query_config.get('aggregations', {})
            query['aggs'] = self._apply_params(aggs_config, runtime_params)

        if 'sort' in query_config:
            query['sort'] = query_config.get('sort')

        return query



    def _apply_params(self, template, params):
        """Recursively apply parameters to a template, including keys."""
        if isinstance(template, dict):
            new_dict = {}
            for k, v in template.items():
                new_key = k
                if isinstance(k, str) and k.startswith('{{') and k.endswith('}}'):
                    keyname = k[2:-2].strip()
                    new_key = params.get(keyname, k)
                new_dict[new_key] = self._apply_params(v, params)
            return new_dict
        elif isinstance(template, list):
            return [self._apply_params(i, params) for i in template]
        elif isinstance(template, str) and template.startswith('{{') and template.endswith('}}'):
            key = template[2:-2].strip()
            return params.get(key, template) # Replace with param value or keep original template
        else:
            return template

    def _build_range_clause(self, rule_params, runtime_params):
        field = rule_params.get('field')
        if not field:
            return None
        context = rule_params.get('context', 'must')
        # Start with default range_params from config
        range_params = {k: v for k, v in rule_params.items() if k not in ['field', 'context']}

        # Override with runtime_params if they exist
        if 'gte' in runtime_params:
            range_params['gte'] = runtime_params['gte']
        if 'lte' in runtime_params:
            range_params['lte'] = runtime_params['lte']

        if not range_params:
            return None
        template = {"range": {field: range_params}, "context": context}
        return self._apply_params(template, runtime_params)

    def _build_match_clause(self, rule_params, runtime_params):
        field = rule_params.get('field')
        value = rule_params.get('value')
        context = rule_params.get('context', 'must')
        if field and value is not None:
            template = {"match": {field: value}, "context": context}
            return self._apply_params(template, runtime_params)
        return None

    def _build_term_filter_clause(self, rule_params, runtime_params):
        field = rule_params.get('field')
        value = rule_params.get('value')
        # 解析可能的模板值以判断空字符串
        resolved_value = value
        if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
            key = value[2:-2].strip()
            resolved_value = runtime_params.get(key, value)
        if field and (resolved_value is not None) and (str(resolved_value).strip() != ''):
            context = rule_params.get('context', 'filter')
            template = {"term": {field: value}, "context": context}
            return self._apply_params(template, runtime_params)
        return None

    def _build_match_phrase_clause(self, rule_params, runtime_params):
        if isinstance(rule_params, list):
            clauses = []
            for p in rule_params:
                field = p.get('field')
                value = p.get('value')
                exclude = p.get('exclude', False)
                context = 'must_not' if exclude else p.get('context', 'filter')
                if field and value is not None:
                    clause = {"match_phrase": {field: value}, "context": context}
                    clauses.append(self._apply_params(clause, runtime_params))
            return clauses
        else:
            field = rule_params.get('field')
            value = rule_params.get('value')
            exclude = rule_params.get('exclude', False)
            context = 'must_not' if exclude else rule_params.get('context', 'must')
            if field and value is not None:
                clause = {"match_phrase": {field: value}, "context": context}
                return self._apply_params(clause, runtime_params)
        return None

    def _build_regexp_clause(self, rule_params, runtime_params):
        field = rule_params.get('field')
        value = rule_params.get('value')
        context = rule_params.get('context', 'must')
        if field and value is not None:
            template = {"regexp": {field: {"value": value}}, "context": context}
            return self._apply_params(template, runtime_params)
        return None

    def _build_exists_clause(self, rule_params, runtime_params):
        field_param = rule_params.get('field')
        if not field_param:
            return None

        fields = [field_param] if isinstance(field_param, str) else field_param

        context = rule_params.get('context', 'filter')
        clauses = []
        for field in fields:
            if field:
                template = {"exists": {"field": field}, "context": context}
                clauses.append(self._apply_params(template, runtime_params))

        return clauses

    def _build_not_exists_clause(self, rule_params, runtime_params):
        field_param = rule_params.get('field')
        if not field_param:
            return None

        fields = [field_param] if isinstance(field_param, str) else field_param

        clauses = []
        for field in fields:
            if field:
                # The context for not_exists is implicitly 'must_not'
                template = {"exists": {"field": field}, "context": "must_not"}
                clauses.append(self._apply_params(template, runtime_params))

        return clauses

    def _build_terms_clause(self, rule_params, runtime_params):
        if isinstance(rule_params, list):
            clauses = []
            for p in rule_params:
                field = p.get('field')
                values = p.get('values')
                exclude = p.get('exclude', False)
                context = 'must_not' if exclude else p.get('context', 'filter')
                if field and values:
                    template = {"terms": {field: values}, "context": context}
                    clauses.append(self._apply_params(template, runtime_params))
            return clauses
        else:
            field = rule_params.get('field')
            values = rule_params.get('values')
            exclude = rule_params.get('exclude', False)
            context = 'must_not' if exclude else rule_params.get('context', 'filter')
            if field and values:
                template = {"terms": {field: values}, "context": context}
                return self._apply_params(template, runtime_params)
        return None

    def _build_multi_match_clause(self, rule_params, runtime_params):
        fields = rule_params.get('fields')
        query = rule_params.get('query')
        context = rule_params.get('context', 'must')
        if fields and (query is not None) and (str(query).strip() != ''):
            multi_match_params = {k: v for k, v in rule_params.items() if k not in ['context']}
            template = {"multi_match": multi_match_params, "context": context}
            return self._apply_params(template, runtime_params)
        return None

    def _build_bool_clause(self, rule_params, runtime_params):
        bool_query = {}
        for condition in ['must', 'should', 'must_not', 'filter']:
            if condition in rule_params:
                clauses = []
                for rule in rule_params[condition]:
                    rule_name = next(iter(rule))
                    rule_builder = self.rule_builders.get(rule_name)
                    if rule_builder:
                        # Note: This is a simplified recursive call. It assumes the nested rule's
                        # parameters are directly within the rule definition (e.g., {'term': {'field': ...}})).
                        # It doesn't handle complex, multi-level nested 'params' sections like the top-level query does.
                        clause = rule_builder(rule[rule_name], runtime_params)
                        if clause:
                            # The context from the inner clause is ignored, as it's defined by the bool condition.
                            if 'context' in clause:
                                del clause['context']
                            clauses.append(clause)
                if clauses:
                    bool_query[condition] = clauses

        if bool_query:
            context = rule_params.get('context', 'must')
            return {"bool": bool_query, "context": context}

        return None

    def _apply_params(self, template, runtime_params):

        if isinstance(template, dict):
            new_dict = {}
            for k, v in template.items():
                new_key = k
                if isinstance(k, str) and k.startswith('{{') and k.endswith('}}'):
                    keyname = k[2:-2].strip()
                    new_key = runtime_params.get(keyname, k)
                new_dict[new_key] = self._apply_params(v, runtime_params)
            return new_dict
        elif isinstance(template, list):
            return [self._apply_params(i, runtime_params) for i in template]
        elif isinstance(template, str) and template.startswith('{{') and template.endswith('}}'):
            key = template[2:-2].strip()
            return runtime_params.get(key, template)
        else:
            return template