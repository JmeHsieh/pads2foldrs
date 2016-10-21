from copy import deepcopy
import json
import logging
from os.path import abspath, dirname, join
from urllib.parse import urlparse

from bs4 import BeautifulSoup, SoupStrainer
from hackpads import Hackpads


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%I:%M:%S %p')


def get_repo_info(config_path, repo_dir):
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except OSError:
        logging.error("Can't read config file")
        return None
    else:
        repo_url_key = 'hackpad_repo_url'
        if repo_url_key not in config:
            logging.error("Can't find {} key in config".format(repo_url_key))
            return None

    repo_url = config[repo_url_key]
    repo_path = join(repo_dir, urlparse(repo_url).path.split('/')[-1].split('.')[0])
    return (repo_url, repo_path)


def get_last_commit(file_path):
    try:
        with open(file_path, 'r') as f:
            last_commit = f.read()
    except OSError:
        last_commit = None
    return last_commit


def update_last_commit(sha, file_path):
    logging.info('update latest commit sha')
    with open(file_path, 'w') as f:
        f.write(sha)


def _find_new_foldrs(diff_pads, pads_path):
    """ Construct new hackfoldr indexes by
    scanning hackfoldr links from hackpad htmls """

    pad_index_fn = 'pads.json'
    with open(join(pads_path, pad_index_fn), 'r') as f:
        pads = json.load(f)
        pads = [p for p in pads if p['padid'] in diff_pads]

    foldrs = {}
    for pad in pads:
        pad_id = pad['padid']

        with open(join(pads_path, '{}.html').format(pad_id), 'r') as f:
            html = f.read()

        logging.info('scanning {}.html'.format(pad_id))

        for link in BeautifulSoup(html, "html.parser", parse_only=SoupStrainer('a')):
            if link.has_attr('href'):
                url = link['href']
                parsed = urlparse(url)
                paths = parsed.path.split('/')
                if 'hackfoldr.org' not in parsed.netloc:
                    continue
                if len(paths) < 2 or not paths[1]:
                    continue

                foldr_url = parsed._replace(path=''.join(paths[:2])).geturl()
                foldr_id = paths[1]
                if foldr_id not in foldrs:
                    foldrs[foldr_id] = {'url': foldr_url, 'hackpads': set()}
                if 'beta' in parsed.netloc:
                    foldrs[foldr_id]['url'] = foldr_url
                foldrs[foldr_id]['hackpads'].add(pad_id)

    return foldrs


def _merged_foldr(old, new):
    _old = deepcopy(old)
    _new = deepcopy(new)
    for k, v in _new.items():
        if isinstance(v, list):
            _o = set(_old.get(k, []))
            _n = set(v)
            _u = _o | _n
            _old.update({k: sorted(list(_u))})
        elif isinstance(v, set):
            _u = _old.get(k, set()) | v
            _old.update({k: _u})
        elif isinstance(v, dict):
            raise NotImplementedError
        else:
            if k in _old and k == 'url' and 'beta' not in v:
                continue
            _old.update({k: v})
    return _old


def gen_foldr_index(diff_pads, pads_path, out_dir):
        fn = 'foldrs.json'

        # merge old w/ new
        try:
            with open(join(out_dir, fn), 'r') as f:
                old = json.load(f)
                for v in old.values():
                    v.update({'hackpads': set(v.get('hackpads', []))})
        except OSError:
            old = {}
        new = _find_new_foldrs(diff_pads, pads_path)
        mix = {_id: _merged_foldr(old.get(_id, {}), new.get(_id, {}))
               for _id in old.keys() | new.keys()}

        # convert 'hackpads' from set to list
        clean = {_id: f.update({'hackpads': sorted(list(f['hackpads']))}) or f
                 for _id, f in mix.items()}

        # write foldrs.json
        with open(join(out_dir, fn), 'w') as f:
            json.dump(clean, f, sort_keys=True, indent=2, ensure_ascii=False)

        logging.info('write {}'.format(fn))


def main():
    base_dir = dirname(abspath(__file__))
    data_dir = join(base_dir, '_data')
    config_fn = 'config.json'
    last_commit_fn = 'last_commit.txt'

    repo_info = get_repo_info(join(base_dir, config_fn), data_dir)
    if repo_info:
        repo_url, repo_path = repo_info
    else:
        return

    hackpads = Hackpads(repo_url, repo_path)
    hackpads.remote().pull()

    last_commit = get_last_commit(join(data_dir, last_commit_fn))
    diff_pads = hackpads.get_diff_pads(last_commit)
    if diff_pads:
        logging.info('current commit:{}'.format(hackpads.head.commit))
        logging.info('last commit:{}'.format(last_commit))
        logging.info('diff pads: {}'.format('\n' + '\n'.join(diff_pads)))
    else:
        logging.info('no diff pads since last scan.')
        return

    gen_foldr_index(diff_pads, hackpads.working_dir, data_dir)
    update_last_commit(str(hackpads.head.commit), join(data_dir, last_commit_fn))


if __name__ == '__main__':
    main()
