Feature: Atomic text writes
  write_text_atomic writes a temp file then os.replace, so a durable artifact is never left
  half-written: a reader sees the old content or the complete new content, never a partial.

  Rule: A complete write replaces the target with the full content

    Scenario: writing creates the file and any missing parent directories
      Given a target path in a not-yet-existing directory
      When I atomically write "hello world"
      Then the file exists with content "hello world"

  Rule: A failed write corrupts nothing and leaves no temp file

    Scenario: a failure during replace keeps the original content intact
      Given an existing file containing "original"
      And the replace step will fail
      When I atomically write "new" expecting failure
      Then the file still contains "original"
      And no temporary files remain in the directory

  Rule: The published file gets ordinary permissions, not the temp file's owner-only mode

    Scenario: an atomically written file is as readable as a plainly written one
      Given a target path in a not-yet-existing directory
      When I atomically write "hello world"
      Then the file's permission bits equal those of a plainly written sibling file
