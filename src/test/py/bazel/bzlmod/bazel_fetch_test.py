# pylint: disable=g-backslash-continuation
# Copyright 2023 The Bazel Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# pylint: disable=g-long-ternary

import os
import tempfile
from absl.testing import absltest
from src.test.py.bazel import test_base
from src.test.py.bazel.bzlmod.test_utils import BazelRegistry
from src.test.py.bazel.bzlmod.test_utils import scratchFile


class BazelFetchTest(test_base.TestBase):

  def setUp(self):
    test_base.TestBase.setUp(self)
    self.registries_work_dir = tempfile.mkdtemp(dir=self._test_cwd)
    self.main_registry = BazelRegistry(
      os.path.join(self.registries_work_dir, 'main')
    )
    self.ScratchFile(
      '.bazelrc',
      [
        # In ipv6 only network, this has to be enabled.
        # 'startup --host_jvm_args=-Djava.net.preferIPv6Addresses=true',
        'common --enable_bzlmod',
        'build --experimental_isolated_extension_usages',
        'build --registry=' + self.main_registry.getURL(),
        # We need to have BCR here to make sure built-in modules like
        # bazel_tools can work.
        'build --registry=https://bcr.bazel.build',
        'build --verbose_failures',
        # Set an explicit Java language version
        'build --java_language_version=8',
        'build --tool_java_language_version=8',
        'build --lockfile_mode=update',
        ],
    )
    self.ScratchFile('WORKSPACE')
    # The existence of WORKSPACE.bzlmod prevents WORKSPACE prefixes or suffixes
    # from being used; this allows us to test built-in modules actually work
    self.ScratchFile('WORKSPACE.bzlmod')

  def testFetchAll(self):
    self.ScratchFile(
      'MODULE.bazel',
      [
        'ext = use_extension("extension.bzl", "ext")',
        'use_repo(ext, "hello")',
        'local_path_override(module_name="bazel_tools", path="tools_mock")',
      ],
    )
    self.ScratchFile('BUILD')
    self.ScratchFile(
      'extension.bzl',
      [
        'def _repo_rule_impl(ctx):',
        '    ctx.file("WORKSPACE")',
        '    ctx.file("BUILD", "filegroup(name=\'lala\')")',
        'repo_rule = repository_rule(implementation=_repo_rule_impl)',
        '',
        'def _ext_impl(ctx):',
        '    print("I was called!")',
        '    repo_rule(name="hello")',
        'ext = module_extension(implementation=_ext_impl)',
      ],
    )

    self.ScratchFile('tools_mock/BUILD')
    self.ScratchFile('tools_mock/WORKSPACE')
    self.ScratchFile('tools_mock/MODULE.bazel', ['module(name="bazel_tools")'])
    self.ScratchFile('tools_mock/tools/build_defs/repo/BUILD')
    self.CopyFile(self.Rlocation('io_bazel/tools/build_defs/repo/http.bzl'),
                                 'tools_mock/tools/build_defs/repo/http.bzl')
    self.CopyFile(self.Rlocation('io_bazel/tools/build_defs/repo/utils.bzl'),
                                 'tools_mock/tools/build_defs/repo/utils.bzl')

    _, _, stderr = self.RunBazel(['fetch', '--all'])
    self.assertIn('I was called!', ''.join(stderr))
    _, _, stderr = self.RunBazel(['build', '--fetch=false', '@hello//:all'])
    self.assertNotIn('I was called!', ''.join(stderr))

if __name__ == '__main__':
  absltest.main()
