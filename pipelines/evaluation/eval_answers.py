"""Compare generators on identical frozen R2 excerpts, without retrieval variance.

python -m pipelines.evaluation.eval_answers --server fused=http://localhost:8080 \
    --server instruct=http://localhost:8081 --output .amp/in/artifacts/answer-comparison.json

Term/length checks are diagnostics, NOT factual correctness scores. Review every
answer against its rubric and context before choosing a generator. Different
model sizes/quantizations cannot isolate the effect of fine-tuning.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx

from apps.backend.core.prompt import chat_messages
from apps.backend.core.textutil import sentences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', action='append', required=True, metavar='LABEL=URL')
    parser.add_argument('--cases', type=Path, default=Path(__file__).with_name('answer_cases.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    fixture = json.loads(args.cases.read_text())
    results = []
    with httpx.Client(timeout=300) as client:
        for server in args.server:
            label, url = server.split('=', 1)
            for case in fixture['cases']:
                context = fixture['sources'][case['source']]['context']
                messages = chat_messages(context, case['question'])
                started = time.perf_counter()
                response = client.post(url.rstrip('/') + '/v1/chat/completions', json={
                    'messages': messages, 'temperature': 0.0, 'max_tokens': 768,
                    'chat_template_kwargs': {'enable_thinking': False},
                })
                response.raise_for_status()
                payload = response.json()
                choice = payload['choices'][0]
                answer = choice['message']['content'].strip()
                count = len(sentences(answer, min_len=1))
                terms = [any(term.casefold() in answer.casefold() for term in group)
                         for group in case['expected_terms']]
                result = dict(
                    server=label, model=payload.get('model'), case=case['id'],
                    question=case['question'], context=context, messages=messages,
                    answer=answer, seconds=round(time.perf_counter() - started, 2),
                    finish_reason=choice.get('finish_reason'), usage=payload.get('usage'),
                    sentence_count=count, term_checks=terms,
                    diagnostic_pass=(all(terms) and count >= case['min_sentences']
                                     and count <= case.get('max_sentences', 100)),
                    rubric=case['rubric'], manual_verdict=None,
                )
                results.append(result)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2))
                print(f'{label}/{case["id"]}: {answer}', flush=True)


if __name__ == '__main__':
    main()
