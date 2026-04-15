# Theme Customization Guide

## Quick Color Customization

All colors are controlled by CSS variables in `templates/qa_app/base.html`. To change the theme, simply edit the `:root` section at the top of the file.

### Main Color Variables

```css
:root {
    --primary-color: #007cba;        /* Main brand color */
    --primary-dark: #005a87;         /* Darker shade */
    --primary-light: #e6f4f8;        /* Light background */
    --header-bg: #007cba;            /* Header background */
    --header-text: #ffffff;          /* Header text */
}
```

## Pre-made Color Schemes

### Blue Theme (Default)
```css
--primary-color: #007cba;
--header-bg: #007cba;
```

### Green Theme
```css
--primary-color: #28a745;
--header-bg: #28a745;
```

### Purple Theme
```css
--primary-color: #6f42c1;
--header-bg: #6f42c1;
```

### Dark Theme
```css
--primary-color: #495057;
--header-bg: #343a40;
--light-bg: #f8f9fa;
```

## Customizing the Header

### Change Logo Text

Edit `templates/qa_app/base.html`:
```html
<a href="{% url 'qa_app:dashboard' %}" class="logo">
    🏭 QA Workflow Automation  <!-- Change this text -->
</a>
```

### Add Logo Image

Replace the logo text with an image:
```html
<a href="{% url 'qa_app:dashboard' %}" class="logo">
    <img src="{% static 'images/logo.png' %}" alt="QA Workflow" style="height: 40px;">
</a>
```

### Change Header Height

In `base.html`, modify the header padding:
```css
.header {
    padding: 1rem 2rem;  /* Change these values */
}
```

## Customizing Navigation Menu

### Add/Remove Menu Items

Edit `templates/qa_app/base.html`:
```html
<ul class="nav-menu">
    <li><a href="{% url 'qa_app:dashboard' %}">Dashboard</a></li>
    <li><a href="{% url 'qa_app:product_list' %}">Products</a></li>
    <li><a href="/admin/">Admin</a></li>
    <!-- Add more items here -->
</ul>
```

## Customizing Cards and Tables

### Card Styling

Cards use the `.card` class. To customize:
```css
.card {
    background: white;
    border-radius: 8px;      /* Roundness */
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);  /* Shadow */
    padding: 1.5rem;          /* Spacing */
}
```

### Table Styling

Tables automatically use the theme colors. To customize:
```css
thead {
    background-color: var(--primary-color);  /* Header color */
    color: white;
}
```

## Customizing Buttons

### Button Colors

Buttons use these classes:
- `.btn-primary` - Primary actions (uses --primary-color)
- `.btn-secondary` - Secondary actions
- `.btn-success` - Success actions (green)
- `.btn-warning` - Warning actions (yellow)
- `.btn-danger` - Danger actions (red)

### Button Sizes

Add size classes:
```css
.btn-small {
    padding: 0.25rem 0.75rem;
    font-size: 0.85rem;
}

.btn-large {
    padding: 0.75rem 1.5rem;
    font-size: 1.1rem;
}
```

## Customizing Status Badges

Badges automatically match status colors:
- `.badge-success` - Green
- `.badge-warning` - Yellow
- `.badge-danger` - Red
- `.badge-info` - Blue
- `.badge-secondary` - Gray

## Adding Custom CSS

### Method 1: Edit base.html

Add custom CSS in the `<style>` section of `templates/qa_app/base.html`.

### Method 2: Create separate CSS file

1. Create `static/css/custom.css`
2. Add to `base.html`:
```html
<link rel="stylesheet" href="{% static 'css/custom.css' %}">
```

## Font Customization

Change fonts in `base.html`:
```css
body {
    font-family: 'Your Font', -apple-system, BlinkMacSystemFont, sans-serif;
}
```

## Responsive Design

The theme is responsive by default. Breakpoints:
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

## Examples

### Example 1: Change to Green Theme

Edit `templates/qa_app/base.html`:
```css
:root {
    --primary-color: #28a745;
    --primary-dark: #1e7e34;
    --header-bg: #28a745;
}
```

### Example 2: Add Company Logo

1. Place logo in `static/images/logo.png`
2. Edit `base.html`:
```html
<a href="{% url 'qa_app:dashboard' %}" class="logo">
    <img src="{% static 'images/logo.png' %}" alt="Company Logo" style="height: 40px; vertical-align: middle;">
    <span style="margin-left: 10px;">QA Workflow</span>
</a>
```

### Example 3: Custom Footer

Edit footer section in `base.html`:
```html
<footer class="footer">
    <p>&copy; {% now "Y" %} Your Company Name. All rights reserved.</p>
    <p>Contact: support@company.com | Phone: +1-234-567-8900</p>
</footer>
```

## Need Help?

- Check `templates/qa_app/base.html` for all CSS variables
- Use browser DevTools to inspect elements
- Test changes in development before deploying


