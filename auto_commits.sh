#!/bin/bash

# ---------------- SETTINGS ----------------
start_day="2025-08-15"
total_days=61
day_start_hour=4
day_end_hour=22
sleep_duration=5
branch_name="main"
# ------------------------------------------

# Make sure we are on main
git checkout -B main

# Fetch latest (avoid rejected push errors)
git fetch origin

# Get tracked & untracked files excluding ignored ones
files=$(git ls-files --others --cached --exclude-standard | shuf)

total_files=$(echo "$files" | wc -l)
echo "Found $total_files valid files. Starting random commits..."

i=0
for file in $files; do

    # Extra safety filters
    [[ "$file" == *"__pycache__"* ]] && continue
    [[ "$file" == *.pyc ]] && continue
    [[ "$file" == *.sh ]] && continue

    # Random day within 63 days
    random_day=$((RANDOM % total_days))

    # Random realistic hour/min/sec
    random_hour=$((day_start_hour + RANDOM % (day_end_hour - day_start_hour)))
    random_minute=$((RANDOM % 60))
    random_second=$((RANDOM % 60))

    commit_date=$(date -d "$start_day +$random_day day" +%Y-%m-%d)
    commit_time=$(printf "%sT%02d:%02d:%02d" "$commit_date" "$random_hour" "$random_minute" "$random_second")

    git add "$file"

    GIT_AUTHOR_DATE="$commit_time" GIT_COMMITTER_DATE="$commit_time" \
    git commit --allow-empty -m "Refactor $(basename "$file")"

    echo "Committed $file at $commit_time"

    git push -f origin "$branch_name"

    sleep $sleep_duration
    ((i++))
done

echo "Done. $i files committed randomly from Aug 15 across 63 days."
