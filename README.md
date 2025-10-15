# Steam Screenshot Utils - Improved Version

A comprehensive, modernized version of the Steam Screenshot Utils tool with enhanced features, better error handling, improved performance, and a sleek web gallery interface.

## 🚀 Key Improvements

### **Architecture & Code Quality**
- **Modern Python Features**: Uses dataclasses, type hints, pathlib, and other modern Python patterns
- **Object-Oriented Design**: Well-structured classes with clear separation of concerns
- **Configuration Management**: Centralized configuration using frozen dataclasses
- **Custom Exceptions**: Proper exception hierarchy for better error handling

### **Enhanced Error Handling & Reliability**
- **Comprehensive Logging**: Proper logging system instead of print statements
- **Retry Logic**: API calls with exponential backoff for better reliability
- **Input Validation**: Robust validation for all inputs and file operations
- **Graceful Degradation**: Handles missing data and API failures gracefully

### **Performance & Features**
- **Progress Tracking**: Real-time progress updates for long operations
- **Better File Management**: Enhanced cross-platform file operations
- **Improved Caching**: Smarter cache management with validation
- **Memory Efficient**: Better handling of large screenshot collections

### **Modern Web Gallery**
- **Dark Theme UI**: Beautiful dark theme with gradient backgrounds
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile
- **Advanced Search**: Search functionality across categories and images
- **Collapsible Categories**: Organized, expandable category sections
- **Lightbox Viewer**: Full-screen image viewing with smooth transitions
- **Natural Sorting**: Intelligent sorting of images and categories

## 📋 Requirements

- Python 3.8+
- `requests` library
- `docopt` library

## 🛠 Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the improved script:
```bash
python ssu2_improved.py --help
```

## 📖 Usage

The improved version maintains the same command-line interface as the original:

```bash
# Backup Steam screenshots
python ssu2_improved.py backup <steam_user_folder> [-o <output_folder>]

# Sort screenshots by app name
python ssu2_improved.py sort <screenshots_folder>

# Merge compressed and uncompressed screenshots
python ssu2_improved.py merge <compressed_folder> <uncompressed_folder>

# Rename appid folders to app names
python ssu2_improved.py rename <screenshots_folder> [-f|--force]

# Generate modern web gallery
python ssu2_improved.py gallery [-d <screenshots_dir>] [-o <output_html>]
```

### **New Features & Options**

- **Enhanced Logging**: Use `-q/--quiet` to suppress non-error output
- **Dry Run Mode**: Use `-n/--dry-run` to preview operations without making changes
- **Force Update**: Use `-u/--update` to force refresh the appid cache
- **Force Rename**: Use `-f/--force` to overwrite existing folders (dangerous!)

## 🎨 Gallery Features

The new gallery generator creates a stunning web interface with:

- **Modern Dark Theme**: Easy on the eyes with gradient backgrounds
- **Responsive Grid Layout**: Adapts to any screen size
- **Search Functionality**: Find specific games or screenshots instantly
- **Collapsible Categories**: Keep your gallery organized
- **Lightbox Viewer**: Click any image for full-screen viewing
- **Smooth Animations**: Polished transitions and hover effects
- **Mobile Optimized**: Perfect experience on all devices

## 🔧 Technical Improvements

### **Code Structure**
- **Modular Design**: Separate classes for different functionalities
- **Type Safety**: Comprehensive type hints throughout
- **Documentation**: Detailed docstrings for all functions
- **Constants Management**: Centralized configuration

### **Error Handling**
- **Custom Exception Classes**: `SSUError`, `AppIdError`, `FileOperationError`, `ValidationError`
- **Graceful Failures**: Continues operation even when individual files fail
- **Detailed Error Messages**: Clear, actionable error reporting

### **Performance**
- **Efficient File Operations**: Optimized file copying and moving
- **Smart Caching**: Validates cache integrity before use
- **Progress Feedback**: Real-time updates for long operations
- **Memory Management**: Handles large collections efficiently

### **Cross-Platform Support**
- **Path Handling**: Uses pathlib for cross-platform compatibility
- **Filename Sanitization**: Handles special characters on Windows/Mac/Linux
- **Encoding**: Proper UTF-8 handling for international characters

## 📊 Comparison with Original

| Feature | Original | Improved |
|---------|----------|----------|
| Error Handling | Basic | Comprehensive with custom exceptions |
| Logging | Print statements | Proper logging system |
| File Operations | Basic | Enhanced with validation and progress |
| Gallery UI | Simple | Modern dark theme with animations |
| Code Structure | Monolithic | Modular OOP design |
| Type Safety | Minimal | Full type hints |
| Performance | Basic | Optimized with progress tracking |
| Cross-Platform | Limited | Full support |
| Documentation | Minimal | Comprehensive docstrings |

## 🔮 Future Enhancements

The improved architecture makes it easy to add:
- **Batch Operations**: Process multiple folders at once
- **Cloud Sync**: Upload galleries to cloud storage
- **Image Optimization**: Automatic resizing and compression
- **Metadata Extraction**: Read EXIF data from screenshots
- **Custom Themes**: Multiple gallery themes
- **Export Options**: PDF exports, zip archives

## 🐛 Migration from Original

The improved version is designed as a drop-in replacement for the original `ssu2.py`. Simply:

1. Replace `ssu2.py` with `ssu2_improved.py`
2. Or rename `ssu2_improved.py` to `ssu2.py`
3. Keep your existing `appid_names.json` cache file

All existing functionality is preserved while adding new features and improvements.

## 📝 License

Same as original - see LICENSE file for details.

## 🙏 Credits

**Original Work:** This project is based on the excellent [Steam Screenshot Utils](https://github.com/kikones34/steam-screenshot-utils) created by [kikones34](https://github.com/kikones34).

The original script provided the foundation and inspiration for this comprehensive modernization. We extend our sincere gratitude to kikones34 for their innovative work in Steam screenshot management.

## 🤝 Contributing

The improved architecture makes it much easier to contribute:
- Clear class structure for new features
- Comprehensive error handling patterns
- Well-documented code for easy understanding
- Modular design for easy testing

---

*Built with ❤️ using modern Python best practices, inspired by kikones34's original vision*
