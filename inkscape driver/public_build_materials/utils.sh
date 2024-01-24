#! /bin/bash

# Utilities for building the packages and installers

set -e # exit on error

function get_files_from_repo {
  local repo_url=$1
  local repo=$2
  local branch=$3
  local subdir=$4
  local target_dir=$5

  if [ ! -d $repo ]; then # if the repo is not there, download it via git
    git clone --filter=blob:none --quiet $repo_url --branch "$branch"
  fi
  if [ -n "$subdir" ]; then # copy files; otherwise don't copy
    cp -r $repo/$subdir/* $target_dir
  fi
}
