FROM drydock/microbase:{{%TAG%}}

# cexec
ADD ./requirements.txt /home/shippable/cexec/requirements.txt
RUN cd /home/shippable/cexec && pip install -r requirements.txt
ADD . /home/shippable/cexec
RUN mkdir -p /home/shippable/cexec/logs
