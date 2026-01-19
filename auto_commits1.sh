#!/bin/bash

# Start date (YYYY-MM-DD)
start_day="2025-11-28"

# Total range of days commits can appear in
total_days=73

# Daily active hours
day_start_hour=4
day_end_hour=22

# Push delay
sleep_duration=8

# Get current branch
branch_name=$(git rev-parse --abbrev-ref HEAD)

# Get files
files=$(find . -type f \
  -not -path "./.git/*" \
  -not -path "./node_modules/*" \
  -not -name "$(basename "$0")" | shuf)

total_files=$(echo "$files" | wc -l)
echo "Found $total_files files. Committing randomly..."

i=0
for file in $files; do
    [[ "$file" == *".sh" ]] && continue

    # Random day offset
    random_day=$((RANDOM % total_days))

    # 20% chance to simulate "no work days"
    skip_chance=$((RANDOM % 10))
    if [ $skip_chance -lt 2 ]; then
        random_day=$((random_day + RANDOM % 3))
    fi

    # Random hour/min/sec
    random_hour=$((day_start_hour + RANDOM % (day_end_hour - day_start_hour)))
    random_minute=$((RANDOM % 60))
    random_second=$((RANDOM % 60))

    commit_date=$(date -d "$start_day +$random_day day" +%Y-%m-%d)
    commit_time=$(printf "%sT%02d:%02d:%02d" "$commit_date" "$random_hour" "$random_minute" "$random_second")

    git add "$file"
    GIT_AUTHOR_DATE="$commit_time" GIT_COMMITTER_DATE="$commit_time" \
    git commit -m "Refactor $(basename "$file")"

    echo "Committed $file at $commit_time"

    git push origin "$branch_name"

    sleep $sleep_duration
    ((i++))
done

echo "Done. $i files committed randomly."
