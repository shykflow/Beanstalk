This project is meant to be developed inside VSCode's extension
[Remote - Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).
Git should behave the same both inside and outside the container.

When using VSCode's **Remote - Containers** extension,
VSCode will automatically pick the correct `python` interpreter for this project.

You can ensure your dev container rebuilds the same way every time with your extenstions installed
by copying /.devcontainer/devcontainer.json.example to /.devcontainer/devcontainer.json
and configuring based on your needs.
