# Image Upload - Quick Reference

## What Changed

✅ **New Features:**
- Upload employee images when registering
- Upload images when creating employees
- Update employee images anytime

✅ **Files Modified:**
1. `serializers.py` - Added RegisterSerializer with image field
2. `views.py` - Updated register endpoint to handle images
3. `settings.py` - Added MEDIA_URL and MEDIA_ROOT
4. `urls.py` - Added media file serving

✅ **New Capabilities:**
- Images stored in `media/profiles/`
- Automatic unique file naming
- Accessible via REST API
- Supports PNG, JPG, GIF, WebP

---

## Restart Server Required

⚠️ **Must restart Django server for changes to take effect:**

```bash
# Terminal 1: Stop and restart
Ctrl+C  # Stop current server

# Start again:
cd fdpp_ems
daphne -b 0.0.0.0 -p 8000 fdpp_ems.asgi:application
```

---

## Quick Upload Examples

### Register with Image

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -F "username=john_doe" \
  -F "email=john@example.com" \
  -F "password=secure_password123" \
  -F "first_name=John" \
  -F "phone=03001234567" \
  -F "CNIC=12345-1234567-1" \
  -F "address=123 Main St" \
  -F "relative=Jane Doe" \
  -F "r_phone=03009876543" \
  -F "r_address=456 Side St" \
  -F "profile_img=@/path/to/photo.jpg"
```

### Create Employee with Image

```bash
curl -X POST http://localhost:8000/api/employees/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "emp_id=15" \
  -F "name=Alice Smith" \
  -F "phone=03009876543" \
  -F "CNIC=99999-9999999-9" \
  -F "address=456 Main Ave" \
  -F "relative=Bob Smith" \
  -F "r_phone=03001234567" \
  -F "r_address=789 Family St" \
  -F "profile_img=@/path/to/photo.jpg"
```

---

## Key Features

| Feature | Details |
|---------|---------|
| **Upload Point 1** | Register new user with image |
| **Upload Point 2** | Create new employee with image |
| **Upload Point 3** | Update employee image anytime |
| **Storage** | `/media/profiles/` directory |
| **Access** | Via REST API with URL |
| **Formats** | PNG, JPG, GIF, WebP |
| **Size Limit** | Up to 5 MB recommended |

---

## API Endpoints

```
POST /api/auth/register/          - Register + image upload
POST /api/employees/               - Create employee + image upload
PUT /api/employees/{emp_id}/       - Update employee image
GET /api/employees/{emp_id}/       - Get employee with image URL
```

---

## Response Example

```json
{
    "emp_id": 10,
    "name": "John Doe",
    "profile_img": "http://localhost:8000/media/profiles/photo_abc123.jpg",
    "phone": "03001234567",
    "status": "active"
}
```

---

## Display in Frontend

### HTML
```html
<img src="http://localhost:8000/media/profiles/photo_abc123.jpg" 
     alt="Employee Profile"
     width="200" height="200" style="border-radius: 50%;">
```

### React
```jsx
<img src={employee.profile_img} alt={employee.name} />
```

---

## How It Works

1. **User/Employee submits form with image**
2. **API receives multipart/form-data**
3. **Image saved to `/media/profiles/`**
4. **Image URL returned in response**
5. **Frontend displays image using URL**

---

## Important Notes

⚠️ **Critical:**
- Use `multipart/form-data` for uploads (automatic with forms)
- Image is **optional** (not required)
- Don't use JSON format for file uploads
- Don't base64-encode images
- Just pass the file directly

---

## File Organization

```
d:\FDPP attendence\fdpp_ems\
├── media/
│   └── profiles/                ← Images stored here
│       ├── photo_abc123.jpg
│       ├── employee_xyz789.jpg
│       └── ...
├── manage.py
└── ...
```

---

## Troubleshooting

**Image upload fails?**
- Use multipart/form-data (not JSON)
- Check file exists and is valid image
- Ensure file size < 5 MB
- Restart Django server

**Image URL returns 404?**
- Make sure server is running
- Image should be at `/media/profiles/filename`
- Check DEBUG=True in settings

**Can't see uploaded images?**
- Restart server after first upload
- Check images directory exists
- Verify media files configured in urls.py

---

## Complete Workflow

### Step 1: Restart Server
```bash
Ctrl+C  # Stop current
cd fdpp_ems
daphne -b 0.0.0.0 -p 8000 fdpp_ems.asgi:application
```

### Step 2: Register with Image
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -F "username=john" -F "email=john@example.com" \
  -F "password=secure123" -F "first_name=John" \
  -F "phone=03001234567" -F "CNIC=12345-1234567-1" \
  -F "address=123 Street" -F "relative=Jane" \
  -F "r_phone=03009876543" -F "r_address=456 Ave" \
  -F "profile_img=@/local/path/photo.jpg"
```

### Step 3: View Image
```
# Copy URL from response, e.g.:
http://localhost:8000/media/profiles/photo_abc123.jpg

# Open in browser to verify
```

### Step 4: Use in Frontend
```html
<img src="http://localhost:8000/media/profiles/photo_abc123.jpg">
```

---

## Summary

✅ Image upload during registration working  
✅ Image upload during employee creation working  
✅ Images automatically stored and served  
✅ Image URLs in all API responses  
✅ Images accessible from frontend  

Everything is configured and ready! 🚀

For complete details, see: **IMAGE_UPLOAD_GUIDE.md**
