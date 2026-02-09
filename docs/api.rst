API Reference
=============

Module-Level API
----------------

The ``chorelib`` module exports a default ``RuleSet`` instance and convenience
decorators. For most use cases, you can use these directly without creating a
``RuleSet`` manually.

.. code-block:: python

   import chorelib

   @chorelib.rule("output.txt", depends="input.txt")
   def build(target, depends, needs):
       chorelib.shell("cp", depends[0], target)

   @chorelib.task
   def clean():
       chorelib.shell("rm -f output.txt")

   if __name__ == "__main__":
       chorelib.Main().run()

Decorators
^^^^^^^^^^

.. attribute:: chorelib.rule

   Decorator to register a file-based build rule on the default ``RuleSet``.
   See :meth:`RuleSet.rule` for parameters.

.. attribute:: chorelib.task

   Decorator to register a task on the default ``RuleSet``.
   See :meth:`RuleSet.task` for parameters.

.. attribute:: chorelib.mtime

   Decorator to register a custom mtime function on the default ``RuleSet``.
   See :meth:`RuleSet.mtime` for parameters.

Global Settings
^^^^^^^^^^^^^^^

.. attribute:: chorelib.verbose
   :type: int

   Global verbosity level controlling message output.
   Set automatically from ``-v`` flags by ``Main``.

   - ``0`` — normal (default)
   - ``1`` — verbose
   - ``2`` — debug messages
   - ``3+`` — logging debug output

RuleSet
-------

.. autoclass:: chorelib.ruledef.RuleSet
   :members: rule, task, mtime
   :undoc-members:

Main
----

.. autoclass:: chorelib.depmain.Main
   :members: run, build, add_arguments, parse_args, get_default_targets
   :undoc-members:

schedule
--------

.. autofunction:: chorelib.deprunner.schedule

Utility Functions
-----------------

shell
^^^^^

.. autofunction:: chorelib.utils.shell

command
^^^^^^^

.. autofunction:: chorelib.utils.command

message
^^^^^^^

.. autofunction:: chorelib.utils.message

flatten
^^^^^^^

.. autofunction:: chorelib.utils.flatten

Exceptions
----------

.. autoclass:: chorelib.errors.RuleError
   :members:

.. autoclass:: chorelib.errors.RuleNotFoundError
   :members:

.. autoclass:: chorelib.errors.TargetNotFoundError
   :members:
