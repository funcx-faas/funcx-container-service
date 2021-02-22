import shlex

# flake8: noqa E501

HEADER = r"""
FROM buildpack-deps:bionic

# avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Set up locales properly
RUN apt-get -qq update && \
    apt-get -qq install --yes --no-install-recommends locales > /dev/null && \
    apt-get -qq purge && \
    apt-get -qq clean && \
    rm -rf /var/lib/apt/lists/*

RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen

ENV LC_ALL en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8

# Use bash as default shell, rather than sh
ENV SHELL /bin/bash

# Set up user
ENV NB_USER funcx_container
ENV HOME /home/${NB_USER}
ENV NB_UID 1000

RUN groupadd \
        --gid ${NB_UID} \
        ${NB_USER} && \
    useradd \
        --comment "Default user" \
        --create-home \
        --gid ${NB_UID} \
        --no-log-init \
        --shell /bin/bash \
        --uid ${NB_UID} \
        ${NB_USER}

RUN wget --quiet -O - https://deb.nodesource.com/gpgkey/nodesource.gpg.key |  apt-key add - && \
    DISTRO="bionic" && \
    echo "deb https://deb.nodesource.com/node_10.x $DISTRO main" >> /etc/apt/sources.list.d/nodesource.list && \
    echo "deb-src https://deb.nodesource.com/node_10.x $DISTRO main" >> /etc/apt/sources.list.d/nodesource.list

# Base package installs are not super interesting to users, so hide their outputs
# If install fails for some reason, errors will still be printed
RUN apt-get -qq update && \
    apt-get -qq install --yes --no-install-recommends \
       less \
       nodejs \
       unzip \
       > /dev/null && \
    apt-get -qq purge && \
    apt-get -qq clean && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 8888

# Environment variables required for build
ENV APP_BASE /srv
ENV NPM_DIR ${APP_BASE}/npm
ENV NPM_CONFIG_GLOBALCONFIG ${NPM_DIR}/npmrc
ENV CONDA_DIR ${APP_BASE}/conda
ENV NB_PYTHON_PREFIX ${CONDA_DIR}/envs/notebook
ENV KERNEL_PYTHON_PREFIX ${NB_PYTHON_PREFIX}
# Special case PATH
ENV PATH ${NB_PYTHON_PREFIX}/bin:${CONDA_DIR}/bin:${NPM_DIR}/bin:${PATH}
# If scripts required during build are present, copy them

RUN ( echo '# enable conda and activate the notebook environment' && \
echo 'CONDA_PROFILE="${CONDA_DIR}/etc/profile.d/conda.sh"' && \
echo 'test -f $CONDA_PROFILE && . $CONDA_PROFILE' && \
echo 'if [[ "${KERNEL_PYTHON_PREFIX}" != "${NB_PYTHON_PREFIX}" ]]; then' && \
echo '    # if the kernel is a separate env, stack them' && \
echo '    # so both are on PATH, notebook first' && \
echo '    conda activate ${KERNEL_PYTHON_PREFIX}' && \
echo '    conda activate --stack ${NB_PYTHON_PREFIX}' && \
echo '' && \
echo '    # even though it'"'"'s second on $PATH' && \
echo '    # make sure CONDA_DEFAULT_ENV is the *kernel* env' && \
echo '    # so that `!conda install PKG` installs in the kernel env' && \
echo '    # where user packages are installed, not the notebook env' && \
echo '    # which only contains UI when the two are different' && \
echo '    export CONDA_DEFAULT_ENV="${KERNEL_PYTHON_PREFIX}"' && \
echo else && \
echo '    conda activate ${NB_PYTHON_PREFIX}' && \
echo fi ) > /etc/profile.d/activate-conda.sh

RUN ( echo 'name: r2d' && \
echo channels: && \
echo '  - conda-forge' && \
echo '  - defaults' && \
echo '  - conda-forge/label/broken' && \
echo dependencies: && \
echo '  - _libgcc_mutex=0.1=conda_forge' && \
echo '  - _openmp_mutex=4.5=0_gnu' && \
echo '  - alembic=1.3.3=py_0' && \
echo '  - async_generator=1.10=py_0' && \
echo '  - attrs=19.3.0=py_0' && \
echo '  - backcall=0.1.0=py_0' && \
echo '  - bleach=3.1.0=py_0' && \
echo '  - blinker=1.4=py_1' && \
echo '  - ca-certificates=2019.11.28=hecc5488_0' && \
echo '  - certifi=2019.11.28=py37_0' && \
echo '  - certipy=0.1.3=py_0' && \
echo '  - cffi=1.13.2=py37h8022711_0' && \
echo '  - chardet=3.0.4=py37_1003' && \
echo '  - cryptography=2.8=py37h72c5cf5_1' && \
echo '  - decorator=4.4.1=py_0' && \
echo '  - defusedxml=0.6.0=py_0' && \
echo '  - entrypoints=0.3=py37_1000' && \
echo '  - idna=2.8=py37_1000' && \
echo '  - importlib_metadata=1.5.0=py37_0' && \
echo '  - inflect=4.0.0=py37_1' && \
echo '  - ipykernel=5.1.4=py37h5ca1d4c_0' && \
echo '  - ipython=7.11.1=py37h5ca1d4c_0' && \
echo '  - ipython_genutils=0.2.0=py_1' && \
echo '  - ipywidgets=7.5.1=py_0' && \
echo '  - jaraco.itertools=5.0.0=py_0' && \
echo '  - jedi=0.16.0=py37_0' && \
echo '  - jinja2=2.11.0=py_0' && \
echo '  - json5=0.8.5=py_0' && \
echo '  - jsonschema=3.2.0=py37_0' && \
echo '  - jupyter_client=5.3.4=py37_1' && \
echo '  - jupyter_core=4.6.1=py37_0' && \
echo '  - jupyter_telemetry=0.0.4=py_0' && \
echo '  - jupyterhub-base=1.1.0=py37_2' && \
echo '  - jupyterhub-singleuser=1.1.0=py37_2' && \
echo '  - jupyterlab=1.2.6=py_0' && \
echo '  - jupyterlab_server=1.0.6=py_0' && \
echo '  - krb5=1.16.4=h2fd8d38_0' && \
echo '  - ld_impl_linux-64=2.33.1=h53a641e_8' && \
echo '  - libcurl=7.65.3=hda55be3_0' && \
echo '  - libedit=3.1.20170329=hf8c457e_1001' && \
echo '  - libffi=3.2.1=he1b5a44_1006' && \
echo '  - libgcc-ng=9.2.0=h24d8f2e_2' && \
echo '  - libgomp=9.2.0=h24d8f2e_2' && \
echo '  - libsodium=1.0.17=h516909a_0' && \
echo '  - libssh2=1.8.2=h22169c7_2' && \
echo '  - libstdcxx-ng=9.2.0=hdf63c60_2' && \
echo '  - mako=1.1.0=py_0' && \
echo '  - markupsafe=1.1.1=py37h516909a_0' && \
echo '  - mistune=0.8.4=py37h516909a_1000' && \
echo '  - more-itertools=8.2.0=py_0' && \
echo '  - nbconvert=5.6.1=py37_0' && \
echo '  - nbformat=5.0.4=py_0' && \
echo '  - ncurses=6.1=hf484d3e_1002' && \
echo '  - notebook=6.0.3=py37_0' && \
echo '  - nteract_on_jupyter=2.1.3=py_0' && \
echo '  - oauthlib=3.0.1=py_0' && \
echo '  - openssl=1.1.1d=h516909a_0' && \
echo '  - pamela=1.0.0=py_0' && \
echo '  - pandoc=2.9.1.1=0' && \
echo '  - pandocfilters=1.4.2=py_1' && \
echo '  - parso=0.6.0=py_0' && \
echo '  - pexpect=4.8.0=py37_0' && \
echo '  - pickleshare=0.7.5=py37_1000' && \
echo '  - pip=20.0.2=py37_0' && \
echo '  - prometheus_client=0.7.1=py_0' && \
echo '  - prompt_toolkit=3.0.3=py_0' && \
echo '  - ptyprocess=0.6.0=py_1001' && \
echo '  - pycparser=2.19=py37_1' && \
echo '  - pycurl=7.43.0.5=py37h16ce93b_0' && \
echo '  - pygments=2.5.2=py_0' && \
echo '  - pyjwt=1.7.1=py_0' && \
echo '  - pyopenssl=19.1.0=py37_0' && \
echo '  - pyrsistent=0.15.7=py37h516909a_0' && \
echo '  - pysocks=1.7.1=py37_0' && \
echo '  - python=3.7.6=h357f687_2' && \
echo '  - python-dateutil=2.8.1=py_0' && \
echo '  - python-editor=1.0.4=py_0' && \
echo '  - python-json-logger=0.1.11=py_0' && \
echo '  - pyzmq=18.1.1=py37h1768529_0' && \
echo '  - readline=8.0=hf8c457e_0' && \
echo '  - requests=2.22.0=py37_1' && \
echo '  - ruamel.yaml=0.16.6=py37h516909a_0' && \
echo '  - ruamel.yaml.clib=0.2.0=py37h516909a_0' && \
echo '  - send2trash=1.5.0=py_0' && \
echo '  - setuptools=45.1.0=py37_0' && \
echo '  - six=1.14.0=py37_0' && \
echo '  - sqlalchemy=1.3.13=py37h516909a_0' && \
echo '  - sqlite=3.30.1=hcee41ef_0' && \
echo '  - terminado=0.8.3=py37_0' && \
echo '  - testpath=0.4.4=py_0' && \
echo '  - tk=8.6.10=hed695b0_0' && \
echo '  - tornado=6.0.3=py37h516909a_0' && \
echo '  - traitlets=4.3.3=py37_0' && \
echo '  - urllib3=1.25.7=py37_0' && \
echo '  - wcwidth=0.1.8=py_0' && \
echo '  - webencodings=0.5.1=py_1' && \
echo '  - wheel=0.34.1=py37_0' && \
echo '  - widgetsnbextension=3.5.1=py37_0' && \
echo '  - xz=5.2.4=h14c3975_1001' && \
echo '  - zeromq=4.3.2=he1b5a44_2' && \
echo '  - zipp=2.1.0=py_0' && \
echo '  - zlib=1.2.11=h516909a_1006' && \
echo 'prefix: /opt/conda/envs/r2d' ) > /tmp/environment.yml

RUN ( echo '#!/bin/bash' && \
echo '# This downloads and installs a pinned version of miniconda' && \
echo 'set -ex' && \
echo '' && \
echo 'cd $(dirname $0)' && \
echo MINICONDA_VERSION=4.7.12.1 && \
echo CONDA_VERSION=4.7.12 && \
echo '# Only MD5 checksums are available for miniconda' && \
echo '# Can be obtained from https://repo.continuum.io/miniconda/' && \
echo 'MD5SUM="81c773ff87af5cfac79ab862942ab6b3"' && \
echo '' && \
echo 'URL="https://repo.continuum.io/miniconda/Miniconda3-${MINICONDA_VERSION}-Linux-x86_64.sh"' && \
echo INSTALLER_PATH=/tmp/miniconda-installer.sh && \
echo '' && \
echo '# make sure we don'"'"'t do anything funky with user'"'"'s $HOME' && \
echo '# since this is run as root' && \
echo 'unset HOME' && \
echo '' && \
echo 'wget --quiet $URL -O ${INSTALLER_PATH}' && \
echo 'chmod +x ${INSTALLER_PATH}' && \
echo '' && \
echo '# check md5 checksum' && \
echo 'if ! echo "${MD5SUM}  ${INSTALLER_PATH}" | md5sum  --quiet -c -; then' && \
echo '    echo "md5sum mismatch for ${INSTALLER_PATH}, exiting!"' && \
echo '    exit 1' && \
echo fi && \
echo '' && \
echo 'bash ${INSTALLER_PATH} -b -p ${CONDA_DIR}' && \
echo 'export PATH="${CONDA_DIR}/bin:$PATH"' && \
echo '' && \
echo '# Allow easy direct installs from conda forge' && \
echo 'conda config --system --add channels conda-forge' && \
echo '' && \
echo '# Do not attempt to auto update conda or dependencies' && \
echo 'conda config --system --set auto_update_conda false' && \
echo 'conda config --system --set show_channel_urls true' && \
echo '' && \
echo '# bug in conda 4.3.>15 prevents --set update_dependencies' && \
echo 'echo '"'"'update_dependencies: false'"'"' >> ${CONDA_DIR}/.condarc' && \
echo '' && \
echo '# install conda itself' && \
echo 'if [[ "${CONDA_VERSION}" != "${MINICONDA_VERSION}" ]]; then' && \
echo '    conda install -yq conda==${CONDA_VERSION}' && \
echo fi && \
echo '' && \
echo '# avoid future changes to default channel_priority behavior' && \
echo 'conda config --system --set channel_priority "flexible"' && \
echo '' && \
echo 'echo "installing notebook env:"' && \
echo 'cat /tmp/environment.yml' && \
echo 'conda env create -p ${NB_PYTHON_PREFIX} -f /tmp/environment.yml' && \
echo '' && \
echo '# empty conda history file,' && \
echo '# which seems to result in some effective pinning of packages in the initial env,' && \
echo '# which we don'"'"'t intend.' && \
echo '# this file must not be *removed*, however' && \
echo 'echo '"'"''"'"' > ${NB_PYTHON_PREFIX}/conda-meta/history' && \
echo '' && \
echo 'if [[ -f /tmp/kernel-environment.yml ]]; then' && \
echo '    # install kernel env and register kernelspec' && \
echo '    echo "installing kernel env:"' && \
echo '    cat /tmp/kernel-environment.yml' && \
echo '' && \
echo '    conda env create -p ${KERNEL_PYTHON_PREFIX} -f /tmp/kernel-environment.yml' && \
echo '    ${KERNEL_PYTHON_PREFIX}/bin/ipython kernel install --prefix "${NB_PYTHON_PREFIX}"' && \
echo '    echo '"'"''"'"' > ${KERNEL_PYTHON_PREFIX}/conda-meta/history' && \
echo '    conda list -p ${KERNEL_PYTHON_PREFIX}' && \
echo fi && \
echo '' && \
echo '# Clean things out!' && \
echo 'conda clean --all -f -y' && \
echo '' && \
echo '# Remove the big installer so we don'"'"'t increase docker image size too much' && \
echo 'rm ${INSTALLER_PATH}' && \
echo '' && \
echo '# Remove the pip cache created as part of installing miniconda' && \
echo 'rm -rf /root/.cache' && \
echo '' && \
echo 'chown -R $NB_USER:$NB_USER ${CONDA_DIR}' && \
echo '' && \
echo 'conda list -n root' && \
echo 'conda list -p ${NB_PYTHON_PREFIX}' ) > /tmp/install-miniconda.bash

RUN mkdir -p ${NPM_DIR} && \
chown -R ${NB_USER}:${NB_USER} ${NPM_DIR}

USER ${NB_USER}
RUN npm config --global set prefix ${NPM_DIR}

USER root
RUN bash /tmp/install-miniconda.bash && \
rm /tmp/install-miniconda.bash /tmp/environment.yml


# Allow target path repo is cloned to be configurable
ARG REPO_DIR=${HOME}
ENV REPO_DIR ${REPO_DIR}
WORKDIR ${REPO_DIR}

# We want to allow two things:
#   1. If there's a .local/bin directory in the repo, things there
#      should automatically be in path
#   2. postBuild and users should be able to install things into ~/.local/bin
#      and have them be automatically in path
#
# The XDG standard suggests ~/.local/bin as the path for local user-specific
# installs. See https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
ENV PATH ${HOME}/.local/bin:${REPO_DIR}/.local/bin:${PATH}

# The rest of the environment
ENV CONDA_DEFAULT_ENV ${KERNEL_PYTHON_PREFIX}
# Run pre-assemble scripts! These are instructions that depend on the content
# of the repository but don't access any files in the repository. By executing
# them before copying the repository itself we can cache these steps. For
# example installing APT packages.
USER root
RUN chown -R ${NB_USER}:${NB_USER} ${REPO_DIR}

"""

APT = r"""
RUN apt-get -qq update && \
apt-get install --yes --no-install-recommends {} && \
apt-get -qq purge && \
apt-get -qq clean && \
rm -rf /var/lib/apt/lists/*

"""

PIP = r"""
USER ${{NB_USER}}
RUN ${{KERNEL_PYTHON_PREFIX}}/bin/pip install --no-cache-dir {}

"""

CONDA = r"""USER root
RUN chown -R ${{NB_USER}}:${{NB_USER}} ${{REPO_DIR}}
USER ${{NB_USER}}
RUN conda install -p ${{NB_PYTHON_PREFIX}} {} && \
conda clean --all -f -y && \
conda list -p ${{NB_PYTHON_PREFIX}}

"""

FOOTER = r"""
# Container image Labels!
# Put these at the end, since we don't want to rebuild everything
# when these change! Did I mention I hate Dockerfile cache semantics?

LABEL repo2docker.ref="None"
LABEL repo2docker.repo="local"
LABEL repo2docker.version="0.11.0"

USER root

# Add start script
# Add entrypoint
RUN ( echo '#!/bin/bash -l' && \
echo '# lightest possible entrypoint that ensures that' && \
echo '# we use a login shell to get a fully configured shell environment' && \
echo '# (e.g. sourcing /etc/profile.d, ~/.bashrc, and friends)' && \
echo 'if [[ ! -z "${R2D_ENTRYPOINT:-}" ]]; then' && \
echo '    exec "$R2D_ENTRYPOINT" "$@"' && \
echo else && \
echo '    exec "$@"' && \
echo fi ) > /usr/local/bin/repo2docker-entrypoint && \
chmod a+x /usr/local/bin/repo2docker-entrypoint

# We always want containers to run as non-root
USER ${NB_USER}

ENTRYPOINT ["/usr/local/bin/repo2docker-entrypoint"]

# Specify the default command to run
CMD ["jupyter", "notebook", "--ip", "0.0.0.0"]
"""


def emit_apt(apt_pkgs):
    if not apt_pkgs:
        return ''
    return APT.format(' '.join([shlex.quote(x) for x in apt_pkgs]))


def emit_conda(conda_pkgs):
    if not conda_pkgs:
        return ''
    return CONDA.format(' '.join([shlex.quote(x) for x in conda_pkgs]))


def emit_pip(pip_pkgs):
    if not pip_pkgs:
        return ''
    return PIP.format(' '.join([shlex.quote(x) for x in pip_pkgs]))


def emit_dockerfile(apt_pkgs, conda_pkgs, pip_pkgs):
    return HEADER + emit_apt(apt_pkgs or []) + emit_conda(conda_pkgs or []) + emit_pip(pip_pkgs or []) + FOOTER
