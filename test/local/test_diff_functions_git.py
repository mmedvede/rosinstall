#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import subprocess
import tempfile

import rosinstall
import rosinstall.helpers

import test.scm_test_base
from test.scm_test_base import AbstractSCMTest, _add_to_file, ROSINSTALL_CMD

class RosinstallDiffGitTest(AbstractSCMTest):

    @classmethod
    def setUpClass(self):
        AbstractSCMTest.setUpClass()
        remote_path = os.path.join(self.test_root_path, "remote")
        os.makedirs(remote_path)
        
        # create a "remote" repo
        subprocess.check_call(["git", "init"], cwd=remote_path)
        subprocess.check_call(["touch", "fixed.txt"], cwd=remote_path)
        subprocess.check_call(["touch", "modified.txt"], cwd=remote_path)
        subprocess.check_call(["touch", "modified-fs.txt"], cwd=remote_path)
        subprocess.check_call(["touch", "deleted.txt"], cwd=remote_path)
        subprocess.check_call(["touch", "deleted-fs.txt"], cwd=remote_path)
        subprocess.check_call(["git", "add", "*"], cwd=remote_path)
        subprocess.check_call(["git", "commit", "-m", "modified"], cwd=remote_path)

        # rosinstall the remote repo and fake ros
        _add_to_file(os.path.join(self.local_path, ".rosinstall"), u"- other: {local-name: ../ros}\n- git: {local-name: clone, uri: remote}")

        cmd = [ROSINSTALL_CMD, "ws", "-n"]
        call = subprocess.Popen(cmd, cwd=self.test_root_path, stdout=subprocess.PIPE)
        output=call.communicate()[0]

        clone_path = os.path.join(self.local_path, "clone")
        
        # make local modifications
        subprocess.check_call(["rm", "deleted-fs.txt"], cwd=clone_path)
        subprocess.check_call(["git", "rm", "deleted.txt"], cwd=clone_path)
        _add_to_file(os.path.join(clone_path, "modified-fs.txt"), u"foo\n")
        _add_to_file(os.path.join(clone_path, "modified.txt"), u"foo\n")
        subprocess.check_call(["git", "add", "modified.txt"], cwd=clone_path)
        _add_to_file(os.path.join(clone_path, "added-fs.txt"), u"tada\n")
        _add_to_file(os.path.join(clone_path, "added.txt"), u"flam\n")
        subprocess.check_call(["git", "add", "added.txt"], cwd=clone_path)
                
    def check_diff_output(self, output):
        # sha ids are always same with git
        self.assertEqual('diff --git clone/added.txt clone/added.txt\nnew file mode 100644\nindex 0000000..8d63207\n--- /dev/null\n+++ clone/added.txt\n@@ -0,0 +1 @@\n+flam\ndiff --git clone/deleted-fs.txt clone/deleted-fs.txt\ndeleted file mode 100644\nindex e69de29..0000000\ndiff --git clone/deleted.txt clone/deleted.txt\ndeleted file mode 100644\nindex e69de29..0000000\ndiff --git clone/modified-fs.txt clone/modified-fs.txt\nindex e69de29..257cc56 100644\n--- clone/modified-fs.txt\n+++ clone/modified-fs.txt\n@@ -0,0 +1 @@\n+foo\ndiff --git clone/modified.txt clone/modified.txt\nindex e69de29..257cc56 100644\n--- clone/modified.txt\n+++ clone/modified.txt\n@@ -0,0 +1 @@\n+foo\n\n', output)
        
    def test_Rosinstall_diff_git_outside(self):
        """Test diff output for git when run outside workspace"""
        cmd = [ROSINSTALL_CMD, "ws", "--diff"]        
        call = subprocess.Popen(cmd, cwd=self.test_root_path, stdout=subprocess.PIPE)
        output=call.communicate()[0]
        self.check_diff_output(output)
        

    def test_Rosinstall_diff_git_inside(self):
        """Test diff output for git when run inside workspace"""
        directory = self.test_root_path + "/ws"
        cmd = [ROSINSTALL_CMD, ".", "--diff"]        
        call = subprocess.Popen(cmd, cwd=directory, stdout=subprocess.PIPE)
        output=call.communicate()[0]

        self.check_diff_output(output)
        
    def test_Rosinstall_status_git_inside(self):
        """Test status output for git when run inside workspace"""
        directory = self.test_root_path + "/ws"
        cmd = [ROSINSTALL_CMD, ".", "--status"]        
        call = subprocess.Popen(cmd, cwd=directory, stdout=subprocess.PIPE)
        output=call.communicate()[0]
        self.assertEqual('A       clone/added.txt\n D      clone/deleted-fs.txt\nD       clone/deleted.txt\n M      clone/modified-fs.txt\nM       clone/modified.txt\n\n', output)
   
    def test_Rosinstall_status_git_outside(self):
        """Test status output for git when run outside workspace"""
        cmd = [ROSINSTALL_CMD, "ws", "--status"]        
        call = subprocess.Popen(cmd, cwd=self.test_root_path, stdout=subprocess.PIPE)
        output=call.communicate()[0]
        self.assertEqual('A       clone/added.txt\n D      clone/deleted-fs.txt\nD       clone/deleted.txt\n M      clone/modified-fs.txt\nM       clone/modified.txt\n\n', output)

    def test_Rosinstall_status_git_untracked(self):
        """Test untracked status output for git when run outside workspace"""
        cmd = [ROSINSTALL_CMD, "ws", "--status-untracked"]        
        call = subprocess.Popen(cmd, cwd=self.test_root_path, stdout=subprocess.PIPE)
        output=call.communicate()[0]

        self.assertEqual('A       clone/added.txt\n D      clone/deleted-fs.txt\nD       clone/deleted.txt\n M      clone/modified-fs.txt\nM       clone/modified.txt\n??      clone/added-fs.txt\n\n', output)
