export PS1="\[\033[01;32m\][OpenRASP] \u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\] # "
export PATH=$PATH:/jdk/bin
export LANG=en_US.UTF-8

alias ls='ls --color=auto'
alias grep='grep --color=auto'
alias ll='ls -lah --color=auto'
alias l='ll'
alias rasp-install='curl -sS https://raw.githubusercontent.com/baidu/openrasp/master/rasp-install/remote/linux/app-env-docker.sh?_=$(date +%s) | bash'

shopt -s autocd
