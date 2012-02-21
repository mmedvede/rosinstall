from __future__ import print_function

import os

import helpers
from helpers import ROSInstallException, get_ros_stack_path, get_ros_package_path
import config
from config import SetupConfigElement

CATKIN_CMAKE_TOPLEVEL="""#
#  TOPLEVEL cmakelists
#
cmake_minimum_required(VERSION 2.8)
cmake_policy(SET CMP0003 NEW)
cmake_policy(SET CMP0011 NEW)

set(CMAKE_CXX_FLAGS_INIT "-Wall")

enable_testing()

include(${CMAKE_SOURCE_DIR}/workspace-config.cmake OPTIONAL)

list(APPEND CMAKE_PREFIX_PATH ${CMAKE_BINARY_DIR} ${CMAKE_BINARY_DIR}/cmake)

file(MAKE_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
file(MAKE_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

if (IS_DIRECTORY ${CMAKE_SOURCE_DIR}/catkin)
  message(STATUS "+++ catkin")
  set(CATKIN_BUILD_PROJECTS "ALL" CACHE STRING
    "List of projects to build, or ALL for all.  Use to completely exclude certain projects from cmake traversal.")
  add_subdirectory(catkin)
else()
  find_package(catkin)
endif()

catkin_workspace()
"""


def generate_setup_sh_text(config, ros_root, ros_package_path):
  # overlay or standard
  text =  """#!/usr/bin/env sh
# THIS IS A FILE AUTO-GENERATED BY rosinstall
# IT IS UNLIKELY YOU WANT TO EDIT THIS FILE BY HAND
# IF YOU WANT TO CHANGE THE ROS ENVIRONMENT VARIABLES
# USE THE rosinstall TOOL INSTEAD.
# see: http://www.ros.org/wiki/rosinstall
"""
  distro_unset = False
  for t in config.get_config_elements():
    if t.setup_file:
      if not distro_unset:
        text += "unset ROS_DISTRO\n"
        distro_unset = True
      text += ". %s\n"%os.path.join(t.path, t.setup_file)
    if isinstance(t, SetupConfigElement):
      if not distro_unset:
        text += "unset ROS_DISTRO\n"
        distro_unset = True
      text += ". %s\n"%t.path

    text += """
if [ -z "${ROS_DISTRO}" ]; then
  export ROS_ROOT=%s 
  export PATH=$ROS_ROOT/bin:$PATH
  export PYTHONPATH=$ROS_ROOT/core/roslib/src:$PYTHONPATH
  if [ ! \"$ROS_MASTER_URI\" ] ; then export ROS_MASTER_URI=http://localhost:11311 ; fi
fi"""% ros_root

    text += """
# python script to read .rosinstall even when rosnistall is not installed
export _ROS_PACKAGE_PATH_ROSINTALL=`/usr/bin/env python << EOPYTHON
import sys, os, yaml;
if not os.path.isfile('.rosinstall'):
    sys.exit("There is no .rosinstall file at %s"%os.path.abspath('.'))
with open(".rosinstall", "r") as f:
  try:
    v=f.read();
  except Exception as e:
    sys.exit("Failed to read .rosinstall file: %s "%str(e))
try:
  y = yaml.load(v);
except Exception as e:
  sys.exit("Invalid yaml in .rosinstall: %s "%str(e))
if y is not None:
  lnames=[x.values()[0]['local-name'] for x in y if x.values() is not None and x.keys()[0] != "setup-file"]
  if len(lnames) == 0:
    sys.exit(".rosinstall contains no path elements")
  print ':'.join(reversed(lnames))
else:
  sys.exit(".rosinstall contains no path elements")
EOPYTHON`
if [ -z $_ROS_PACKAGE_PATH_ROSINTALL ]; then
    echo Error: Udate of ROS_PACKAGE_PATH failed
    return 22
fi
export ROS_PACKAGE_PATH=$_ROS_PACKAGE_PATH_ROSINTALL
unset _ROS_PACKAGE_PATH_ROSINTALL
"""

  text += "export ROS_WORKSPACE=%s\n" % config.get_base_path()
  return text

def generate_setup_bash_text(config, shell):
  if shell == 'bash':
    script_path = """
SCRIPT_PATH="${BASH_SOURCE[0]}";
if([ -h "${SCRIPT_PATH}" ]) then
  while([ -h "${SCRIPT_PATH}" ]) do SCRIPT_PATH=`readlink "${SCRIPT_PATH}"`; done
fi
export OLDPWDBAK=$OLDPWD
pushd . > /dev/null
cd `dirname ${SCRIPT_PATH}` > /dev/null
SCRIPT_PATH=`pwd`;
popd  > /dev/null
export OLDPWD=$OLDPWDBAK
"""
  elif shell == 'zsh':
    script_path = "SCRIPT_PATH=\"$(dirname $0)\";"
  else:
    raise ROSInstallException("%s shell unsupported."%shell);

  text =  """#!/usr/bin/env %(shell)s
# THIS IS A FILE AUTO-GENERATED BY rosinstall
# IT IS UNLIKELY YOU WANT TO EDIT THIS FILE BY HAND
# IF YOU WANT TO CHANGE THE ROS ENVIRONMENT VARIABLES
# USE THE rosinstall TOOL INSTEAD.
# see: http://www.ros.org/wiki/rosinstall

CATKIN_SHELL=%(shell)s

# Load the path of this particular setup.%(shell)s

%(script_path)s

# unset _roscmd to check later whether setup.sh has sourced rosbash
unset -f _roscmd 1> /dev/null 2>&1

. $SCRIPT_PATH/setup.sh

type _roscmd | grep function 1>/dev/null 2>&1
if [ ! $? -eq 0 ]; then
  if rospack help > /dev/null 2>&1; then
    ROSSHELL_PATH=`rospack find rosbash`/ros%(shell)s
    if [ -e $ROSSHELL_PATH ]; then
      . $ROSSHELL_PATH
    fi
  else
    echo "rospack could not be found, you cannot have ros%(shell)s features until you bootstrap ros"
  fi
fi
"""%locals()
  return text


def generate_setup(config):
  # simplest case first
  ros_root = helpers.get_ros_stack_path(config)
  if not ros_root:
    raise ROSInstallException("No 'ros' stack detected.  The 'ros' stack is required in all rosinstall directories. Please add a definition of the 'ros' stack either manually in %s and then call 'rosinstall .' in the directory. Or add one on the command line 'rosinstall . http://www.ros.org/rosinstalls/boxturtle_ros.rosinstall'. Or reference an existing install like in /opt/ros/boxturtle with 'rosinstall . /opt/ros/boxturtle'.  Note: the above suggestions assume you are using boxturtle, if you are using latest or another distro please change the urls."%__ROSINSTALL_FILENAME )
  rpp = ':'.join(helpers.get_ros_package_path(config))
  
  text = generate_setup_sh_text(config, ros_root, rpp)
  setup_path = os.path.join(config.get_base_path(), 'setup.sh')
  with open(setup_path, 'w') as f:
    f.write(text)

  for shell in ['bash', 'zsh']:

    text = generate_setup_bash_text(config, shell)
    setup_path = os.path.join(config.get_base_path(), 'setup.%s'%shell)
    with open(setup_path, 'w') as f:
      f.write(text)
