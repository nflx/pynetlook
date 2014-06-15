pynetlook
=========

# WHAT
  A service that collects netstat like data such as known connections and listening ports of processes,
  and sends it to Logstash. Either directly or via Redis.

  Runs on Windows and Linux.


# LICENSE
  pynetlook copyright (c) 2014 Emil Lind

    pynetlook is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    pynetlook is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with pynetlook.  If not, see <http://www.gnu.org/licenses/>.

# WHY
  I wanted to collect information on all listening services and active 
  connections on a network. As accurate as possible without tapping
  into network infrastructure. That meant it needed to run on all used
  platforms such as windows and linux of different versions. I also 
  wanted it stored in a way to enable powerful searching and vizualisation.

# HOW
  Pynetlook is installed on clients by package freezed with pyinstaller
  or if possibly run directly using existing python installation with 
  required modules installed. When started it periodically sends current
  connections to the logstash server, either directly or via redis.
  I used redis to poll queued data through firewalls into logstash 
  ElasticSearch storage. I then use Kibana for searching the data.

# REQUIREMENTS 
    logstash server
    python modules:
     - python-logstash psutil yaml logstash_formatter dnspython

# ISSUES
  most likely

# INSTALL
    setup logstash server (www.logstash.net)
    install python modules needed (pip install <module>)
    run it (python ./pynetlook.py)
    fix problems
    repeat until it runs
    send me a message to update this instruction with more needed details.
