from sentence_transformers import SentenceTransformer, util
import json
from difflib import SequenceMatcher
import os

model = SentenceTransformer('all-MiniLM-L6-v2')  # Легкая модель

def evaluate_comments(session_id, comments, mr_package_path):
    gt_path = os.path.join(mr_package_path, 'golden_truth.json')
    with open(gt_path, 'r') as f:
        golden_truth = json.load(f)  # list of defects: {'file':, 'line_range':, 'type':, 'text':, ...}

    tp, fp, fn = [], [], golden_truth.copy()
    for comment in comments:
        matched = False
        for defect in golden_truth:
            # (a) Anchor match: check file == and line_range overlap (custom func)
            if not anchor_match(comment['file'], comment['line_range'], defect['file'], defect['line_range']):
                continue
            # (b) Key labels: if comment['type'] in defect['labels']
            if comment['type'] not in defect.get('labels', []):
                continue
            # (c) Semantic: fuzzy + embedding
            fuzzy_ratio = SequenceMatcher(None, comment['text'], defect['text']).ratio()
            emb1 = model.encode(comment['text'])
            emb2 = model.encode(defect['text'])
            cos_sim = util.cos_sim(emb1, emb2)[0][0]
            if fuzzy_ratio > 0.6 or cos_sim > 0.7:
                tp.append(defect)
                fn.remove(defect)
                matched = True
                break
        if not matched:
            fp.append(comment)

    # Compute score по рубрике (весам)
    score = calculate_score(tp, fp, fn, rubric)  # ваша логика
    return {'tp': tp, 'fp': fp, 'fn': fn, 'score': score}