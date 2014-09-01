#!/bin/bash

ORIG_REPO_FILENAME="orig-cfme-repo.repo"
ORIG_REPO_PATH="/tmp/orig-cfme-repo"
NEW_REPO_FILENAME="new-cfme-repo.repo"
NEW_REPO_PATH="/tmp/new-cfme-repo"

# TODO
NEW_REPO_ID="new-cfme"
NEW_REPO_NAME="new-cfme"
NEW_REPO_BASEURL="new-cfme"

function check_root {
    if [ "$EUID" -ne 0 ]; then
        echo "Please run as root."
        exit 1
    fi
}

function get_args {
    if [[ $# -eq 1 ]]; then
        local repo_url="$1"
        $(wget -q --spider "$repo_url")
        if [[ $? -ne 0 ]]; then
            echo "Invalid URL - unable to download specified repo file."
            exit 1
        fi
    else
        echo "\
Usage: $0 URL_TO_REPO_FILE

E.g. $0 http://my.server.com/repos/my_repository.repo
"
        exit 1
    fi
    echo "$repo_url"
}


function download_repo {
    rm -rf "/etc/yum.repos.d/$ORIG_REPO_FILENAME"
    wget "$1" -O "/etc/yum.repos.d/$ORIG_REPO_FILENAME"

    orig_repo_id=$(head -n 1 "/etc/yum.repos.d/$ORIG_REPO_FILENAME" | sed 's/\[//;s/\]//')

    rm -rf "$ORIG_REPO_PATH"
    mkdir "$ORIG_REPO_PATH"

    repotrack -r "$orig_repo_id" -p "$ORIG_REPO_PATH" "*"
}

function create_new_repo {
    rm -rf "$NEW_REPO_PATH"
    mkdir "$NEW_REPO_PATH"

    for file in "$ORIG_REPO_PATH"/*.rpm; do
        rpmrebuild --release=99 -p -d "$NEW_REPO_PATH" --notest-install "$file"
    done

    mkdir "$NEW_REPO_PATH"/.packages
    mv "$NEW_REPO_PATH"/*/* "$NEW_REPO_PATH"/.packages
    rm -rf "$NEW_REPO_PATH"/*
    mv "$NEW_REPO_PATH"/.packages "$NEW_REPO_PATH"/packages
    createrepo -o "$NEW_REPO_PATH" "$NEW_REPO_PATH"/packages 1>/dev/null 2>&1
    return $?
}

# function generate_repo_file {
#     echo "\
# [$NEW_REPO_ID]
# name=CFME-5.3
# baseurl=TODO get url from ARGS (will be based on "upload_new_repo_url")
# gpgcheck=0
# enabled=1
# " > "$NEW_REPO_PATH"/"$NEW_REPO_FILENAME"
# }

# function scp_upload_new_repo {
#    scp -r "$NEW_REPO_PATH" "$user":"$password"@"$server":"$path_on_server"
#}

check_root
repo_url=$(get_args "$@")
if [[ $? -ne 0 ]]; then
    echo "$repo_url"
    exit 1
fi
download_repo "$repo_url"
create_new_repo
#generate_repo_file
#upload_new_repo
