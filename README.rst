Munin Node -> CloudWatch
========================

Installation
------------

You'll need `munin-node` installed and some plugins configured. This is enough
to get started::

    sudo apt install munin-node munin-plugins-extra

You'll need to deploy this code. We provide a python bundle that you can just copy into ``/usr/local/bin``.

You'll need an AWS Access Key. If you are deploying this on EC2 you should use IAM Instance Profiles to grant the EC2 instance a role. Otherwise you could have a per-server user in a group. Either way the policy it needs is::

    {
      "Statement": [{
          "Action": "cloudwatch:PutMetricData",
          "Effect": "Allow",
          "Resource": "*"
      }]
    }

You'll need a cron job::

    crontab -e

    # Mail output can be useful when testing
    MAILTO=your.email@example.com

    # You only need to set these for bare metal servers
    AWS_ACCESS_KEY_ID=youraccesskey
    AWS_SECRET_ACCESS_KEY=yoursecretaccesskey

    4-59/5 * * * * /usr/local/bin/munin-node-to-cloudwatch
