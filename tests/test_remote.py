#!/usr/bin/env python3
"""Destructive acceptance checks for disposable demo services."""
import argparse
import json
import subprocess
import tempfile
import unittest
import uuid
import urllib.error
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--board-url', required=True)
parser.add_argument('--git-url', required=True)
args = parser.parse_args()
BOARD = args.board_url.rstrip('/')
GIT = args.git_url.rstrip('/')


def request(path, method='GET', data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(BOARD + path, body, {'Content-Type': 'application/json'}, method=method)
    try:
        response = urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        return response.status, response.headers.get_content_type(), json.load(response)


class BoardTests(unittest.TestCase):
    def test_board_workflow_and_validation(self):
        self.assertEqual(request('/health'), (200, 'application/json', {'status': 'ok'}))
        status, content_type, task = request('/tasks', 'POST', {'title': 'Review code', 'assignee': 'host'})
        self.assertEqual((status, content_type), (201, 'application/json'))
        self.assertEqual((task['title'], task['description'], task['assignee'], task['status'], task['messages']), ('Review code', '', 'host', 'open', []))
        path = '/tasks/' + str(task['id'])
        self.assertIn(task, request('/tasks')[2])
        self.assertEqual(request(path)[2], task)
        status, _, message = request(path + '/messages', 'POST', {'author': 'agent', 'text': 'Ready'})
        self.assertEqual((status, message), (201, {'author': 'agent', 'text': 'Ready'}))
        status, _, task = request(path, 'PATCH', {'status': 'done', 'description': 'Complete'})
        self.assertEqual((status, task['status'], task['description'], task['messages']), (200, 'done', 'Complete', [message]))
        for payload in ({}, {'title': ''}, {'title': True}, {'title': 'ok', 'extra': 1}):
            self.assertEqual(request('/tasks', 'POST', payload)[0], 400)
        for payload in ({}, {'status': 'bad'}, {'title': ''}, {'assignee': None}, {'id': 1}):
            self.assertEqual(request(path, 'PATCH', payload)[0], 400)
        self.assertEqual(request(path + '/messages', 'POST', {'author': 'x', 'text': ''})[0], 400)
        self.assertEqual(request('/tasks/not-a-number')[0], 404)
        self.assertEqual(request('/tasks/999999999')[0], 404)
        req = urllib.request.Request(BOARD + '/tasks', b'{', {'Content-Type': 'application/json'}, method='POST')
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(error.exception.code, 400)
        error.exception.close()


class GitTests(unittest.TestCase):
    def test_push_and_clone_multiple_repositories(self):
        with urllib.request.urlopen(GIT + '/healthz', timeout=10) as response:
            self.assertEqual(response.status, 200)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            branch = 'main'
            def git(*arguments, cwd=None, check=True):
                return subprocess.run(['git', *map(str, arguments)], cwd=cwd, check=check, capture_output=True, text=True, timeout=60)
            commits = []
            for name in ('rust', 'scala', 'python'):
                work = root / name
                git('clone', f'{GIT}/{name}.git', work)
                git('checkout', '-B', branch, cwd=work)
                git('config', 'user.name', 'Demo test', cwd=work)
                git('config', 'user.email', 'demo@example.invalid', cwd=work)
                content = name + '-' + uuid.uuid4().hex
                (work / 'result.txt').write_text(content, encoding='utf-8')
                git('add', 'result.txt', cwd=work)
                git('commit', '-m', 'Acceptance test', cwd=work)
                commit = git('rev-parse', 'HEAD', cwd=work).stdout.strip()
                git('push', f'{GIT}/{name}.git', branch, cwd=work)
                clone = root / (name + '-clone')
                git('clone', f'{GIT}/{name}.git', clone)
                git('fetch', 'origin', branch, cwd=clone)
                self.assertEqual(git('rev-parse', 'FETCH_HEAD', cwd=clone).stdout.strip(), commit)
                self.assertEqual(git('rev-parse', 'HEAD', cwd=clone).stdout.strip(), commit)
                self.assertEqual((clone / 'result.txt').read_text(encoding='utf-8'), content)
                commits.append(commit)
            self.assertEqual(len(set(commits)), 3)
            self.assertNotEqual(git('push', f'{GIT}/missing.git', branch, cwd=root / 'rust', check=False).returncode, 0)


if __name__ == '__main__':
    unittest.main(argv=['test_remote.py'], verbosity=2)
