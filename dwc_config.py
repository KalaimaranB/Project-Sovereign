"""DWC Network Server Emulator

    Copyright (C) 2014 SMTDDR
    Copyright (C) 2014 kyle95wm
    Copyright (C) 2014 AdmiralCurtiss
    Copyright (C) 2015 Sepalani

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

Configuration module.
"""

import configparser as ConfigParser

import other.utils as utils


import os

def resolve_config_path(filename):
    """Helper to transparently locate configs moved to the config/ repository."""
    if not os.path.isabs(filename) and not filename.startswith('config/'):
        # Anchor to the project root where this coordinator file resides
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(base_dir, 'config', filename)
        if os.path.exists(candidate):
            return candidate
    return filename


def get_config_filename(filename='altwfc.cfg'):
    """Return the config filename that will be used."""
    resolved = resolve_config_path(filename)
    try:
        config = ConfigParser.RawConfigParser(allow_no_value=True)
        config.read(resolved)
        if config.getboolean('Config', 'AlternativeConfig'):
            alt_file = config.get('Config', 'AlternativeConfigFile')
            return resolve_config_path(alt_file)
    except Exception as e:
        pass
    return resolved


def get_ip_port(section, filename='altwfc.cfg'):
    """Return a tuple (IP, Port) of the corresponding section."""
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(get_config_filename(filename))
    return (config.get(section, 'IP'), config.getint(section, 'Port'))


def get_ip(section, filename='altwfc.cfg'):
    """Return the IP of the corresponding section."""
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(get_config_filename(filename))
    return config.get(section, 'IP')


def get_port(section, filename='altwfc.cfg'):
    """Return the port of the corresponding section."""
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(get_config_filename(filename))
    return config.getint(section, 'Port')


def get_logger(section, filename='altwfc.cfg'):
    """Return the logger of the corresponding section."""
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(get_config_filename(filename))
    return utils.create_logger(
        config.get(section, 'LoggerName'),
        config.get(section, 'LoggerFilename'),
        config.getint(section, 'LoggerLevel'),
        config.getboolean(section, 'LoggerOutputConsole'),
        config.getboolean(section, 'LoggerOutputFile')
    )


def get_svchost(section, filename='altwfc.cfg'):
    """Return the svchost of the corresponding section."""
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(get_config_filename(filename))
    return config.get(section, 'SvcHost')
