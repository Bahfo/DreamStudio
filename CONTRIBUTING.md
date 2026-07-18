# Contributing to DreamStudio IDE Open Source

Thank you for your interest in contributing to DreamStudio open-source repository!

## What Kinds of Contributions We Welcome?
The following contain what are the contribution types we need, ordered from the most preferred to the least preferred: 
- **Bug Fixes**: Most contributions we accept are fixes for reporducible issues. Tests should supply those fixes if possible. 
- **Features** (By Prior Agreement Only): If you want to add a new feature, please discuss it with us first. We accept features only when they align with our roadmap for the relevant subsystem. 
- **Documentation**: Documentation is always preferred to be sufficient, and explains the idea in a good way. 
- **Maintinance**: Maintaining the code is not much preferred except when releasing a major update. 

## Commit Message Format for Contributing: 

The standard message format from now on (from Version 1.1.0 and forward) is: 

```git
<Personal ID> <Commit Title>
<Fix Number (Given within the issued Personal ID Ticket)>
<description>
...
<End of commit message (Optional)>
```

*For Example*:
```git
DS110-12345 Bahfo: Fixing Bug in Type Declaration
Number: 12345678
Fixed a smaller issue when opening a code-editor in language X and type of token Y didn't declare correctly. 

Thanks!
```

Avoid, please, linking to any discussions in a commit message. Instead, summarize the discussion right in the commit message. 