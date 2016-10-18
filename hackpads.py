from git.repo.base import NoSuchPathError, Repo


class Hackpads(Repo):

    def __init__(self, repo_url, repo_path):
        try:
            Repo.__init__(self, repo_path)
        except NoSuchPathError:
            Repo.clone_from(repo_url, repo_path)
            Repo.__init__(self, repo_path)

    def get_diff_pads(self, last_commit):
        if not last_commit:
            # 'repo.index.entries.keys()' look something like this:
            # [('file1.html', 0), ('file2.html', 0), ('f3.xxx', 0), ...]
            diff_pads = [k[0][:-len('.html')]
                         for k in self.index.entries.keys() if k[0].endswith('.html')]
        else:
            diffs = self.index.diff(last_commit)
            diff_pads = [d.b_path[:-len('.html')]
                         for d in diffs if d.b_path.endswith('.html')]
        return diff_pads
