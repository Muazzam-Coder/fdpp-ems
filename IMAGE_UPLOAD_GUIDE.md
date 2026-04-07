# Employee Image Upload Guide

## Overview

You can now upload employee profile images when:
1. **Registering a new user** - Upload profile picture during registration
2. **Creating a new employee** - Upload profile picture during employee creation
3. **Updating employee** - Update profile picture for existing employee

---

## Files Created/Modified

✅ **Modified Files:**
- `serializers.py` - Added RegisterSerializer with image upload
- `views.py` - Updated register endpoint to handle images
- `settings.py` - Added MEDIA_URL and MEDIA_ROOT
- `urls.py` - Added media file serving for development

✅ **New Directories (auto-created):**
- `media/` - Stores uploaded images
- `media/profiles/` - Stores profile images

---

## Method 1: Register with Profile Image

### Endpoint
```
POST /api/auth/register/
```

### Request Format (Multipart Form Data)

**Using PowerShell:**
```powershell
$form = @{
    username = "john_doe"
    email = "john@example.com"
    password = "secure_password123"
    first_name = "John"
    last_name = "Doe"
    phone = "03001234567"
    CNIC = "12345-1234567-1"
    address = "123 Main Street"
    relative = "Jane Doe"
    r_phone = "03009876543"
    r_address = "456 Side Street"
    start_time = "09:00:00"
    end_time = "17:00:00"
    shift_type = "morning"
}

$file = Get-Item "C:\path\to\photo.jpg"

$response = Invoke-WebRequest -Method Post `
    -Uri "http://localhost:8000/api/auth/register/" `
    -Form $form `
    -ContentType "multipart/form-data" `
    -Headers @{"Accept" = "application/json"}

$response.Content | ConvertFrom-Json | ConvertTo-Json
```

**Using cURL:**
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -F "username=john_doe" \
  -F "email=john@example.com" \
  -F "password=secure_password123" \
  -F "first_name=John" \
  -F "last_name=Doe" \
  -F "phone=03001234567" \
  -F "CNIC=12345-1234567-1" \
  -F "address=123 Main Street" \
  -F "relative=Jane Doe" \
  -F "r_phone=03009876543" \
  -F "r_address=456 Side Street" \
  -F "shift_type=morning" \
  -F "profile_img=@/path/to/photo.jpg"
```

### Response
```json
{
    "message": "User registered successfully",
    "user": {
        "id": 5,
        "username": "john_doe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe"
    },
    "employee": {
        "emp_id": 10,
        "name": "John Doe",
        "phone": "03001234567",
        "CNIC": "12345-1234567-1",
        "shift_type": "morning",
        "start_time": "09:00:00",
        "end_time": "17:00:00",
        "profile_img": "http://localhost:8000/media/profiles/photo_abc123.jpg"
    }
}
```

---

## Method 2: Create Employee with Image

### Endpoint
```
POST /api/employees/
```

### Request Format (Multipart Form Data)

**Using PowerShell:**
```powershell
$form = @{
    emp_id = 15
    name = "Alice Smith"
    phone = "03009876543"
    CNIC = "99999-9999999-9"
    address = "456 Main Ave"
    relative = "Bob Smith"
    r_phone = "03001234567"
    r_address = "789 Family St"
    shift_type = "morning"
    start_time = "09:00:00"
    end_time = "17:00:00"
    status = "active"
}

$file = Get-Item "C:\path\to\employee_photo.jpg"

$response = Invoke-WebRequest -Method Post `
    -Uri "http://localhost:8000/api/employees/" `
    -Form $form `
    -Headers @{
        "Authorization" = "Bearer YOUR_TOKEN"
        "Accept" = "application/json"
    }

$response.Content | ConvertFrom-Json | ConvertTo-Json
```

**Using cURL:**
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
  -F "shift_type=morning" \
  -F "start_time=09:00:00" \
  -F "end_time=17:00:00" \
  -F "status=active" \
  -F "profile_img=@/path/to/employee_photo.jpg"
```

### Response
```json
{
    "id": 15,
    "emp_id": 15,
    "name": "Alice Smith",
    "profile_img": "http://localhost:8000/media/profiles/employee_photo_xyz789.jpg",
    "phone": "03009876543",
    "CNIC": "99999-9999999-9",
    "shift_type": "morning",
    "start_time": "09:00:00",
    "end_time": "17:00:00",
    "status": "active",
    ...
}
```

---

## Method 3: Update Employee Profile Image

### Endpoint
```
PUT /api/employees/{emp_id}/
```

### Request Format

**Using PowerShell:**
```powershell
$form = @{}

# Only update image (you can update any field)
$file = Get-Item "C:\path\to\new_photo.jpg"

$response = Invoke-WebRequest -Method Put `
    -Uri "http://localhost:8000/api/employees/15/" `
    -Form $form `
    -Headers @{
        "Authorization" = "Bearer YOUR_TOKEN"
        "Accept" = "application/json"
    }
```

**Using cURL:**
```bash
curl -X PUT http://localhost:8000/api/employees/15/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "profile_img=@/path/to/new_photo.jpg"
```

---

## Supported Image Formats

| Format | Extension | Size | Notes |
|--------|-----------|------|-------|
| JPEG | .jpg, .jpeg | Up to 5 MB | Recommended |
| PNG | .png | Up to 5 MB | Good for graphics |
| GIF | .gif | Up to 5 MB | Animated supported |
| WebP | .webp | Up to 5 MB | Modern format |

---

## Image Storage

### Location
```
d:\FDPP attendence\fdpp_ems\media\profiles\
```

### File Naming
Images are automatically stored with unique names:
```
photo_abc123def456.jpg
employee_photo_xyz789uvw.jpg
```

### Access URL
```
http://localhost:8000/media/profiles/photo_abc123def456.jpg
```

### Direct File Path
```
media/profiles/photo_abc123def456.jpg
```

---

## Using Images in Frontend

### Display Employee Profile Picture

**HTML:**
```html
<img src="http://localhost:8000/media/profiles/photo_abc123.jpg" 
     alt="Employee Profile" 
     width="200" 
     height="200"
     style="border-radius: 50%;">
```

**React:**
```jsx
function EmployeeCard({ employee }) {
    return (
        <div>
            <img 
                src={employee.profile_img} 
                alt={employee.name}
                width={200}
                height={200}
                style={{borderRadius: '50%'}}
            />
            <h2>{employee.name}</h2>
        </div>
    )
}
```

**Vue:**
```vue
<template>
    <div>
        <img 
            :src="employee.profile_img" 
            :alt="employee.name"
            width="200"
            height="200"
            style="border-radius: 50%"
        />
        <h2>{{ employee.name }}</h2>
    </div>
</template>
```

---

## Image Upload via Web Form

### HTML Form

```html
<!DOCTYPE html>
<html>
<body>

<h2>Employee Image Upload</h2>

<form id="uploadForm">
    <input type="file" id="imageInput" name="profile_img" accept="image/*" required>
    <input type="text" name="username" placeholder="Username" required>
    <input type="email" name="email" placeholder="Email" required>
    <input type="password" name="password" placeholder="Password" required>
    <input type="text" name="first_name" placeholder="First Name" required>
    <input type="text" name="phone" placeholder="Phone" required>
    <input type="text" name="CNIC" placeholder="CNIC" required>
    <input type="text" name="address" placeholder="Address" required>
    
    <button type="submit">Register</button>
</form>

<script>
document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    
    try {
        const response = await fetch('http://localhost:8000/api/auth/register/', {
            method: 'POST',
            body: formData,
            // Don't set Content-Type header - browser will set it correctly
        });
        
        const data = await response.json();
        
        if (response.ok) {
            console.log('✅ Registration successful!');
            console.log('Profile image URL:', data.employee.profile_img);
        } else {
            console.error('❌ Error:', data);
        }
    } catch (error) {
        console.error('❌ Network error:', error);
    }
});
</script>

</body>
</html>
```

---

## Database Storage

### Employee Model
```python
profile_img = models.ImageField(upload_to='profiles/', null=True, blank=True)
```

### Query Employees with Images

```bash
python manage.py shell
```

```python
from management.models import Employee

# Get employee with image
emp = Employee.objects.get(emp_id=10)
print(f"Image URL: {emp.profile_img.url}")
print(f"Image path: {emp.profile_img.path}")

# Get all employees with images
employees_with_images = Employee.objects.exclude(profile_img='')
for emp in employees_with_images:
    print(f"{emp.name}: {emp.profile_img.url}")

# Get all employees without images
employees_without_images = Employee.objects.filter(profile_img='')
print(f"Employees without images: {employees_without_images.count()}")
```

---

## Important Notes

⚠️ **Key Points:**

1. **Multipart Upload Required**
   - Use `multipart/form-data` content type
   - Don't use JSON for file uploads
   - Browser auto-sets correct content type

2. **File Size Limit**
   - Configure in Django settings if needed
   - Default: 5 MB (recommended)
   - Larger files may slow down API

3. **Required Fields**
   - `profile_img` is **optional** (can register without image)
   - All employee details are still required
   - Pass image as file, not as base64

4. **Production Deployment**
   - Configure static file serving with Nginx/Apache
   - Use cloud storage (S3, Azure) instead of local filesystem
   - Don't serve files directly from Django in production

5. **Image Optimization**
   - Compress images before upload
   - Use JPEG for photos
   - Use PNG for graphics
   - Typical size: 200-500 KB

---

## Troubleshooting

### Error: "Invalid image file"
**Problem:** Uploaded file isn't a valid image  
**Solution:**
- Ensure file is actually an image
- Check file isn't corrupted
- Try different format (JPG, PNG)

### Error: "File too large"
**Problem:** Image exceeds size limit  
**Solution:**
- Compress image before upload
- Use image editor to reduce dimensions
- Save as JPEG instead of PNG

### Error: "Field required" with image
**Problem:** Image field shows as required  
**Solution:**
- Image is optional - you can skip it
- Include empty value if not uploading image
- Or provide a valid image file

### Image URL returns 404
**Problem:** Can't access uploaded image  
**Solution:**
- Ensure server is running in DEBUG=True mode
- Image should be at `/media/profiles/filename.jpg`
- Check image was actually saved to disk

---

## API Reference

### Register Endpoint
```
POST /api/auth/register/
Content-Type: multipart/form-data

Fields:
- username (required)
- email (required)
- password (required)
- first_name (optional)
- last_name (optional)
- phone (optional)
- CNIC (required)
- address (optional)
- relative (optional)
- r_phone (optional)
- r_address (optional)
- shift_type (optional, default: "morning")
- start_time (optional, default: "09:00:00")
- end_time (optional, default: "17:00:00")
- profile_img (optional) - Image file

Response: 201 Created
```

### Employee Create Endpoint
```
POST /api/employees/
Content-Type: multipart/form-data
Authorization: Bearer TOKEN

Fields:
- emp_id (required)
- name (required)
- phone (required)
- CNIC (required)
- address (required)
- relative (required)
- r_phone (required)
- r_address (required)
- shift_type (optional)
- start_time (required)
- end_time (required)
- status (optional, default: "active")
- profile_img (optional) - Image file

Response: 201 Created
```

### Employee Update Endpoint
```
PUT /api/employees/{emp_id}/
Content-Type: multipart/form-data
Authorization: Bearer TOKEN

Fields: Any employee field (all optional)
- name
- profile_img
- phone
- shift_type
- start_time
- end_time
- status
- etc.

Response: 200 OK
```

---

## Summary

✅ Upload images during registration  
✅ Upload images during employee creation  
✅ Update images for existing employees  
✅ Images stored in `/media/profiles/`  
✅ Automatic unique file naming  
✅ PNG, JPG, GIF, WebP supported  
✅ Images accessible via REST API  

Your employee image upload is now ready! 🎉
