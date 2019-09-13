#!/usr/bin/env bash

cleanup() {
	[ -n "${bashrc}" ] && rm -f "${bashrc}"
}

trap cleanup HUP TERM EXIT

PYTHON=${PYTHON:-python3}

pyversion=$(${PYTHON} --version | awk '{print $2}')
topdir=$(cd "$(dirname "$0")"; pwd -P)
bashrc=$(TMPDIR=${topdir} mktemp .devrc-XXXXXX)
make=$(which gmake 2>/dev/null || which make)

if [ -n "${VIRTUAL_ENV}" ]; then
	virtualenv=${VIRTUAL_ENV}
else
	virtualenv=${topdir}/.venv-${pyversion}
fi

if [ ! -d "${virtualenv}" ]; then
	${PYTHON} -m venv "${virtualenv}" || exit 1
fi

# Instructions to run when entering new shell
cat > "${bashrc}" <<-EOF
	[ -f ~/.bashrc ] && source ~/.bashrc
	source "${virtualenv}"/bin/activate
EOF

# Enter developmet shell
if [ -z "$*" ]; then
	/usr/bin/env bash --rcfile "${bashrc}" -i
else
	source "${bashrc}"
	"$@"
fi

# vim: noet
# -*- indent-tabs-mode: t; tab-width: 8; sh-indentation: 8; sh-basic-offset: 8; -*-
