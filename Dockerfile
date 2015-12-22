FROM shipimg/appbase:gcloud

RUN echo 'ALL ALL=(ALL) NOPASSWD:ALL' | tee -a /etc/sudoers

# Upgrade PIP
RUN apt-get remove -y python-pip
RUN easy_install pip

# cexec
ADD ./requirements.txt /home/shippable/cexec/requirements.txt
RUN cd /home/shippable/cexec && pip install -r requirements.txt
ADD . /home/shippable/cexec
RUN mkdir -p /home/shippable/cexec/logs
ENTRYPOINT ["/home/shippable/cexec/boot.sh"]
