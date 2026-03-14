# 1. manage

## 1.1. 为每个用户配置不同的工作目录

每个用户在同一个GitHub账号下管理自己的代码，可以将每个用户的代码保存在不同的文件夹中。你可以在每个用户的家目录下创建不同的工作目录，设置不同的Git配置。

```shell
/home/user1/project1
/home/user2/project2
```

在每个目录下，通过 init 配置为 git 目录

```shell
git init
```

## 1.2. 使用不同的Git配置

为了区分不同用户，可以为每个用户配置不同的Git用户名和邮箱。每个用户都可以在自己文件夹下设置特定的Git配置。

进入每个项目文件夹后，使用以下命令设置Git配置：

```shell
cd /home/user1/project1
git config user.name "User1"
git config user.email "user1@example.com"

cd /home/user2/project2
git config user.name "User2"
git config user.email "user2@example.com"
```

## 1.3. 使用SSH密钥管理

如果多个用户使用相同的GitHub账号，但希望每个用户的提交能够通过SSH密钥来管理（比如方便区分不同的提交者），可以为每个用户创建不同的SSH密钥对并将其添加到GitHub账户中。然后在Git配置中为每个用户设置不同的SSH密钥。

为每个用户生成SSH密钥对：

```shell
ssh-keygen -t rsa -b 4096 -C "user1@example.com" -f ~/.ssh/id_rsa_user1
ssh-keygen -t rsa -b 4096 -C "user2@example.com" -f ~/.ssh/id_rsa_user2
```

在Git配置文件中为每个用户设置特定的SSH密钥：

编辑~/.ssh/config文件，添加以下内容：

```shell
Host github-user1
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_rsa_user1

Host github-user2
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_rsa_user2
```

1. 在 github 进行配对（使用自己账户）
```shell
cat ~/.ssh/id_rsa_user1.pub
```
将输出的内容复制到剪贴板。它应该以ssh-rsa开头，后面是你的公钥。
1. 登录到GitHub账号。
1. 进入GitHub设置页面：
    - 点击右上角的头像，选择 Settings。
    - 在左侧菜单中选择 SSH and GPG keys。
1. 点击 New SSH key 按钮。
1. 在 Title 字段中输入一个名称（例如：my-ssh-key），然后在 Key 字段中粘贴刚才复制的公钥内容。
1. 点击 Add SSH key。

添加远程仓库


如果没有远程仓库，你需要先添加一个远程仓库。假设你想使用git@github-handle999:handle999/YOLO-MonoPed-Depth.git作为远程仓库URL，可以通过以下命令添加：

```shell
git remote add origin git@github-handle999:handle999/YOLO-MonoPed-Depth.git
# 确认生效
git remote -v
# origin  git@github-handle999:handle999/YOLO-MonoPed-Depth.git (fetch)
# origin  git@github-handle999:handle999/YOLO-MonoPed-Depth.git (push)
```

设置别名

```shell
git remote set-url origin git@github-user1:username/repo.git
# 这是你需要替换的部分，具体包括：
# git@: 这是SSH协议下的标准用户名，git是GitHub要求的用户名。
# github-user1: 这是你在~/.ssh/config文件中定义的别名（你为GitHub配置的主机名别名）。你可以自定义，通常用于指定不同的SSH密钥（例如：github-user1，github-user2等）。如果你没有使用配置文件中的别名，直接使用 github.com 作为主机名。
# 替换规则：如果你在~/.ssh/config中配置了多个GitHub账户，github-user1是你用来区分不同账户的别名；如果只使用一个账户，应该是github.com。
# username: 这是你的GitHub用户名（可以在GitHub页面上看到）。需要替换为你的GitHub用户名。
# repo: 这是你要操作的GitHub仓库名。你需要替换为你想要关联的具体仓库名。
```

3. 测试SSH连接

添加完公钥后，验证GitHub是否能正确识别你的密钥。运行以下命令：

```shell
ssh -T git@github.com
# 成功会看到
Hi username! You've successfully authenticated, but GitHub does not provide shell access.
```

更新Git远程URL以使用不同的Host：

```shell
git remote set-url origin git@github-user1:username/repo.git
```
