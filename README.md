# eBay Reseller Manager

A comprehensive desktop application for managing your eBay resale business on Linux. Track inventory, expenses, calculate optimal pricing, and manage your tax obligations - all in one place!

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4.0+-orange.svg)

## ✨ Features

### 📊 Dashboard
- Real-time business metrics
- Revenue and profit tracking
- Inventory valuation
- Expense summaries
- Year-to-date statistics

### 📦 Inventory Management
- Add items before listing with full details
- Track purchase costs, condition, and storage location
- View inventory value and status (In Stock, Listed, Sold)
- Search and filter inventory
- Upload photos and attach notes

### 💵 Expense Tracking
- Record all business expenses
- Mark expenses as tax deductible or not
- Categorize expenses (shipping supplies, storage, equipment, etc.)
- Attach receipt images
- View expense breakdowns by category

### 🏷️ Pricing Calculator
- Calculate optimal listing prices
- Compare free shipping vs. calculated shipping strategies
- Automatic eBay fee calculations (12.9% + $0.30)
- Real shipping cost estimates
- Target profit by dollar amount or margin percentage
- Side-by-side pricing comparison

### 💰 Sold Items Tracking
- Track all sales history
- Calculate net profits
- View profit margins
- Platform tracking (eBay, Amazon, etc.)
- Sales analytics

### 📈 Reports & Analytics
- Business performance reports
- Profit and loss analysis
- Expense breakdown by category
- Tax estimation (quarterly estimates)
- Export-ready data

## 🚀 Installation

### Requirements
- Linux operating system (Ubuntu, Debian, Fedora, etc.)
- Python 3.10 or higher
- Internet connection for initial setup

### Quick Install

1. **Clone the repository:**
```bash
git clone https://github.com/YOUR-USERNAME/ebay-reseller-manager.git
cd ebay-reseller-manager
```

2. **Run the installer:**
```bash
./install.sh
```

The installer will automatically:
- Check for Python 3
- Create a virtual environment
- Install all dependencies
- Set up the database
- Make everything ready to run

3. **Launch the application:**
```bash
./run.sh
```

### Manual Installation

If you prefer to install manually:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python3 src/main.py
```

## 📖 Usage

### Add Your First Inventory Item
1. Go to the "Inventory" tab
2. Click "➕ Add Item"
3. Fill in the details (title, cost, condition, etc.)
4. Save!

### Track an Expense
1. Go to the "Expenses" tab
2. Click "➕ Add Expense"
3. Enter the amount, category, and mark if tax deductible
4. Save!

### Calculate Pricing
1. Go to the "Price Calculator" tab
2. Select an item from inventory (or enter cost manually)
3. Set your target profit
4. Enter weight and dimensions
5. View the pricing comparison!

### Monitor Your Business
- The "Dashboard" tab shows your business overview
- Track revenue, expenses, and profit
- See your estimated tax liability

## 💡 Tips for Success

- **Be Consistent:** Enter items into inventory as soon as you acquire them
- **Track Everything:** Record all expenses, even small ones - they add up!
- **Mark Deductions:** Properly mark tax-deductible expenses
- **Use Pricing Calculator:** Don't guess - use the calculator to maximize profit
- **Check Dashboard Regularly:** Stay on top of your business metrics

## 📁 File Structure

```
ebay-reseller-manager/
├── data/                   # Database storage
│   └── reseller.db        # SQLite database (created on first run)
├── src/                   # Source code
│   ├── gui/              # GUI modules
│   │   ├── dashboard_tab.py
│   │   ├── inventory_tab.py
│   │   ├── expenses_tab.py
│   │   ├── pricing_tab.py
│   │   ├── sold_items_tab.py
│   │   └── reports_tab.py
│   ├── models/           # Data models
│   ├── database.py       # Database handler
│   └── main.py          # Application entry point
├── tests/               # Unit tests
├── requirements.txt     # Python dependencies
├── install.sh          # Installation script
├── run.sh             # Run script
└── README.md          # This file
```

## 🔧 Troubleshooting

### Application won't start

```bash
# Make sure you're in the project directory
cd ebay-reseller-manager

# Try reinstalling
./install.sh

# Check if virtual environment exists
ls venv/

# If not, create it manually
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Import errors

```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Database issues

```bash
# The database will be recreated automatically if missing
# To start fresh, simply delete the database:
rm data/reseller.db

# Then restart the application
./run.sh
```

## 🤝 Contributing

This is an open-source project! Contributions are welcome.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📋 Roadmap

### Phase 1 (Current) ✅
- Inventory management
- Expense tracking
- Pricing calculator
- Dashboard
- Sold items tracking
- Reports

### Phase 2 (Planned)
- eBay API integration
- Market research tools
- Automated listing creation

### Phase 3 (Future)
- Advanced reporting
- Automated workflows
- Export functionality
- Barcode scanning
- Multi-marketplace support (Amazon, Mercari, etc.)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

- **Tax Calculations:** Estimates only - consult a tax professional for accuracy
- **Data Privacy:** All data is stored locally on your computer
- **No Warranty:** Use at your own risk - always verify calculations

## 🙏 Acknowledgments

- **eBay API:** For marketplace integration
- **PyQt6:** For the amazing GUI framework
- **SQLite:** For lightweight database management

## 📞 Support

Having issues or questions?
- Check the Troubleshooting section above
- Review the code - it's well-commented!
- Open an issue on GitHub

---

**Built with ❤️ for eBay resellers who want to run their business professionally.**

Happy Reselling! 🎉
# ebay-reseller-manager
