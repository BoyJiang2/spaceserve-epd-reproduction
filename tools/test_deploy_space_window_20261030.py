"""Local construction tests only; no Git/SSH/credentials or deployment execution."""
import ast
import unittest
from unittest.mock import Mock
from types import SimpleNamespace
import deploy_space_window_20261030 as deployment


class DeploymentTests(unittest.TestCase):
    def test_exact_bootstrap_compiles_without_execution(self):
        source=deployment.server_command('a'*40);ast.parse(source)
        self.assertIn("commit='"+'a'*40+"'",source)
        self.assertIn("base='"+deployment.BASE+"'",source)

    def test_revision_injection_rejected(self):
        for value in ('main','A'*40,"a'; exit",'a'*39):
            with self.assertRaises(ValueError):deployment.server_command(value)

    def test_no_retry_and_new_scope_is_explicit(self):
        source=deployment.server_command('b'*40)
        self.assertIn('stage.mkdir(mode=0o700,exist_ok=False)',source)
        self.assertIn("assets.guard_processes()",source)
        self.assertIn("command(['sparse-checkout','set','spaceserve/runtime','tests','tools'])",source)
        self.assertNotIn("['reset'",source)
        self.assertNotIn("['clean'",source)


class ControlledCommandTests(unittest.TestCase):
    def context(self):
        tree=ast.parse(deployment.server_command('a'*40))
        check=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='check')
        command=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='command')
        self.clock=Mock(return_value=0);self.migration=Mock();self.policy=Mock()
        scope=dict(started=0,cancelled=[],time=SimpleNamespace(monotonic=self.clock),
            policy={'validate':self.policy},p={'snapshot':{},'config':{}},git=['git'],out=object(),
            migration=self.migration,TimeoutError=TimeoutError)
        scope['time'].time=lambda:0
        exec(compile(ast.Module(body=[check,command],type_ignores=[]),'<production-command>','exec'),scope)
        return scope

    def test_git_uses_existing_controlled_cleanup_with_shared_deadline(self):
        scope=self.context();scope['command'](['fetch','bundle','a'*40])
        args=self.migration.command_output.call_args.args
        self.assertEqual(args[0],['git','fetch','bundle','a'*40])
        self.assertEqual(args[2:],(45,360))

    def test_cancelled_stop_cannot_start_git(self):
        scope=self.context();scope['cancelled'].append(15)
        with self.assertRaises(TimeoutError):scope['command'](['checkout','--detach','a'*40])
        self.migration.command_output.assert_not_called()

    def test_work_deadline_refuses_git(self):
        scope=self.context();self.clock.return_value=240
        with self.assertRaises(TimeoutError):scope['command'](['checkout','--detach','a'*40])
        self.migration.command_output.assert_not_called()

    def test_controlled_git_failure_propagates_without_retry(self):
        scope=self.context();self.migration.command_output.side_effect=RuntimeError('known own Git release failed')
        with self.assertRaises(RuntimeError):scope['command'](['fetch','bundle','a'*40])
        self.migration.command_output.assert_called_once()


if __name__=='__main__':unittest.main()
