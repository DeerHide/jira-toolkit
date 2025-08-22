cd ..

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "Warning: You have uncommitted changes. Please commit or stash them first."
    exit 1
fi

# Set core.autocrlf to false
git config core.autocrlf false

# Set core.eol to lf
git config core.eol lf

# Normalize all files in the repository
git add --renormalize .

echo "Git line ending configuration updated. Files have been renormalized."
echo "Review the changes with 'git status' and commit when ready."