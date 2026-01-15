# Contributing to Transcribe RO

Thank you for your interest in contributing to Transcribe RO! This document provides guidelines for contributing to the project.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- A clear, descriptive title
- Steps to reproduce the issue
- Expected behavior vs actual behavior
- Your environment (OS, Python version, etc.)
- Any error messages or logs

### Suggesting Enhancements

We welcome suggestions for new features or improvements! Please:
- Check if the feature has already been requested
- Provide a clear description of the feature
- Explain why this feature would be useful
- Provide examples of how it would work

### Code Contributions

#### Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/transcribe_ro.git
   cd transcribe_ro
   ```

3. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. Set up your development environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

#### Making Changes

1. **Write Clean Code**:
   - Follow PEP 8 style guidelines
   - Use meaningful variable and function names
   - Add comments for complex logic
   - Keep functions focused and concise

2. **Test Your Changes**:
   - Test with different audio formats
   - Test with different model sizes
   - Verify error handling works
   - Check that existing features still work

3. **Update Documentation**:
   - Update README.md if adding new features
   - Add examples for new functionality
   - Update QUICKSTART.md if changing basic usage

4. **Commit Your Changes**:
   ```bash
   git add .
   git commit -m "Add feature: description of your changes"
   ```

5. **Push to Your Fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**:
   - Go to the original repository
   - Click "New Pull Request"
   - Select your fork and branch
   - Provide a clear description of your changes

## Development Guidelines

### Code Style

- Follow PEP 8 Python style guide
- Use 4 spaces for indentation
- Maximum line length: 100 characters
- Use docstrings for functions and classes

### Commit Messages

Write clear commit messages:
```
Add feature: Short description

Longer explanation of what changed and why.
Include any relevant context or reasoning.
```

### Testing

Before submitting a pull request:
1. Test your changes locally
2. Verify all output formats work
3. Test error handling
4. Check memory usage with large files

### Documentation

When adding features:
- Update README.md with new options
- Add examples to examples.sh
- Update QUICKSTART.md if it affects basic usage
- Add inline comments for complex code

## Areas for Contribution

Here are some areas where contributions would be particularly valuable:

### Priority Features
- [ ] Support for batch processing multiple files
- [ ] Progress bar for long transcriptions
- [ ] Configuration file support
- [ ] Better memory management for large files
- [ ] Resume interrupted transcriptions

### Improvements
- [ ] Add more translation services (DeepL, etc.)
- [ ] Improve error messages
- [ ] Add logging functionality
- [ ] Create GUI version
- [ ] Add audio preprocessing (noise reduction)

### Documentation
- [ ] Add video tutorials
- [ ] Create more examples
- [ ] Translate documentation to Romanian
- [ ] Add troubleshooting FAQ

### Testing
- [ ] Add unit tests
- [ ] Add integration tests
- [ ] Create automated test suite
- [ ] Test on more platforms

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Accept constructive criticism gracefully
- Focus on what's best for the project
- Show empathy towards other contributors

### Unacceptable Behavior

- Harassment or discriminatory language
- Personal attacks
- Publishing others' private information
- Other unprofessional conduct

## Questions?

If you have questions about contributing:
- Open an issue with the "question" label
- Check existing issues and discussions
- Reach out to the maintainers

## License

By contributing to Transcribe RO, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in the project README. Thank you for helping make Transcribe RO better!

---

**Happy Contributing! 🎉**
