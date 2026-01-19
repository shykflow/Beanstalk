
# Deployment
Note:
Both the `staging` and `production` environments use the
same configuration files. This keeps `staging` as similar
to `production` as possible.

This guide will using `staging` as the example.

----------------

# Set up a new server
This guide will assume another EC2 instance is being added to the load balancer, but the
steps will be similar for any instance that wants to deploy with a gitlab-runner.

Copying an existing EC2 instance is a lot easier than manually doing these steps. But if
that is not an option, here are the steps for creating a new instance from scratch.

Create a new EC2 instance, give it the SSH key from lastpass so the `ubuntu` sudo user can log in and install `docker`.
The install instructions for docker are left out because they might change in the future, just look
them up. Installing docker should create the docker group automatically.

# Install the gitlab runner
```
curl -L "https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh" | sudo bash
sudo apt-get install gitlab-runner
```
If this does not work google the latest method for installing the gitlab runner.

# Register the gitlab runner
```
sudo gitlab-runner register
```
Then provide it with the values from the gitlab website for registering a runner,
it should be a URL and a token.

Give it a unique tag that isn't taken, the EC2 instances in the load ballancer
are named something like: `staging-runner-api-1`, give it a different number at the end.

When it asks what type of executor, choose `shell`.

To see the config file it generated run and its status
```
sudo cat /etc/gitlab-runner/config.toml
sudo service gitlab-runner status
```

# Add the gitlab-runner user to the docker group
```
sudo usermod -aG docker gitlab-runner
```

then reboot the EC2 instance
```
sudo reboot
```

# Setup deploy key
Be the gitlab-runner user to set up the deploy keys
```
sudo -u gitlab-runner -i
mkdir ~/.ssh
cd .ssh
echo "IdentityFile ~/.ssh/beanstalk_staging_deploy_key" > config
touch beanstalk_staging_deploy_key
```

Use vim or nano to paste in the private key found in lastpass.
Look for `beanstalk deploy keys staging`.

Modify the key's permissions so it is only readable for the gitlab-runner user
```
chmod 400 beanstalk_production_deploy_key
```


# Clone the code base to the EC2 machine
While still being the `gitlab-runner` user
```
cd ~
git clone <ssh url>
cd beanstalk-api
git checkout staging
git config pull.rebase false
git config --global --add safe.directory /beanstalk-api
exit
```

Now as the root user, move the cloned directory to the root of the directory tree
```
sudo mv ~/home/gitlab-runner/beanstalk-api /beanstalk-api
```
For convenience, put sym-link to this folder in the root user's home folder
```
cd ~
ln -s /beanstalk-api beanstalk-api
```

# Make this gitlab runner pull the latest code and build when staging updates
Modify the .gitlab-ci.yml file to tell this runner to pull the code when staging updates.

Locate the `.deploy: &deploy` definition block, below it will be a configuration for deploying
to the api servers and the cron server. Duplicate what is needed and specify this new runner.

Push a commit to the `staging` and it should rebuild on all runners watching the staging branch.
