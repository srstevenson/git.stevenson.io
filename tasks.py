import os
import pathlib
import shutil
import tempfile
from typing import List, NamedTuple

import requests
from invoke import task
from invoke.context import Context


class Repo(NamedTuple):
    name: str
    url: str
    desc: str


def create_output_dir():
    """Create output directory."""
    shutil.rmtree("public", ignore_errors=True)
    os.makedirs("public")


def clone_and_build_stagit(ctx: Context, dest: str) -> None:
    """Clone and build stagit."""
    ctx.run(f"git clone https://github.com/srstevenson/stagit.git {dest}")
    with ctx.cd(dest):
        ctx.run("make")


def list_github_repos() -> List[Repo]:
    """List GitHub repositories."""
    response = requests.get("https://api.github.com/users/srstevenson/repos")
    response.raise_for_status()
    return [
        Repo(repo["name"], repo["clone_url"], repo["description"])
        for repo in response.json()
    ]


def clone_repo(ctx: Context, repo: Repo, repos_dir: str) -> None:
    """Clone a GitHub repository and populate metadata files."""
    ctx.run(f"git clone {repo.url} {repos_dir}/{repo.name}")
    git_dir = pathlib.Path(repos_dir) / repo.name / ".git"
    for filename, content in zip(
        ["description", "owner", "url"],
        [repo.desc, "Scott Stevenson", repo.url],
    ):
        (git_dir / filename).write_text(content)


def generate_pages_for_repo(
    ctx: Context, stagit: str, repos_dir: str, name: str
) -> None:
    """Generate the HTML pages for a given repository."""
    os.makedirs(f"public/{name}")
    with ctx.cd(f"public/{name}"):
        ctx.run(f"{stagit} {repos_dir}/{name}")
        ctx.run("cp log.html index.html")
        for filename in ["favicon.png", "logo.png", "style.css"]:
            ctx.run(f"cp ../../static/{filename} .")


def generate_index_page(
    ctx: Context, stagit_index: str, repos_dir: str
) -> None:
    """Generate index.html."""
    ctx.run(f"{stagit_index} {repos_dir}/* > public/index.html")
    for filename in ["favicon.png", "logo.png", "style.css"]:
        ctx.run(f"cp static/{filename} public")


@task
def build(ctx):
    # type: (Context) -> None
    """Build the site."""
    with tempfile.TemporaryDirectory() as stagit_dir:
        create_output_dir()
        clone_and_build_stagit(ctx, stagit_dir)
        repos = list_github_repos()
        stagit = os.path.join(stagit_dir, "stagit")
        stagit_index = os.path.join(stagit_dir, "stagit-index")

        with tempfile.TemporaryDirectory() as repos_dir:
            for repo in repos:
                clone_repo(ctx, repo, repos_dir)
                generate_pages_for_repo(ctx, stagit, repos_dir, repo.name)
            generate_index_page(ctx, stagit_index, repos_dir)
