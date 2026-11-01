# KaamDo Database Schema Design

This document outlines the relational data models and relationships across all modules.

---

## 1. Accounts & Roles (`accounts`)

### `User` (Extends `AbstractUser`)
- `id`: UUID or AutoField (Primary Key)
- `username`: String (Unique)
- `email`: Email (Unique)
- `phone_number`: String (Unique, Indexed)
- `role`: ChoiceField (`CUSTOMER`, `WORKER`, `EMPLOYER`, `FARMER`, `EQUIPMENT_OWNER`)
- `created_at`: DateTime
- `updated_at`: DateTime

---

## 2. Worker Profiles & Discovery (`workers`)

### `WorkerProfile`
- `id`: AutoField (PK)
- `user`: OneToOneField (`accounts.User`, on_delete=CASCADE)
- `bio`: TextField
- `profile_photo`: ImageField
- `primary_skill`: String (Indexed)
- `skills`: JSONField or ManyToManyField (Tags/Skills)
- `experience_years`: Integer
- `hourly_rate`: Decimal(10, 2) (Nullable)
- `daily_rate`: Decimal(10, 2) (Nullable)
- `latitude`: Decimal(9, 6) (Indexed for distance calculation)
- `longitude`: Decimal(9, 6) (Indexed for distance calculation)
- `service_radius_km`: Integer (Default: 20)
- `is_available`: Boolean (Default: True)
- `verification_status`: ChoiceField (`PENDING`, `VERIFIED`, `REJECTED`, Default: `PENDING`)
- `average_rating`: Decimal(3, 2) (Default: 0.0)
- `total_reviews`: Integer (Default: 0)

---

## 3. Jobs & Price Agreements (`jobs`)

### `Job`
- `id`: AutoField (PK)
- `employer`: ForeignKey (`accounts.User`, related_name='posted_jobs')
- `title`: String
- `description`: TextField
- `required_skill`: String
- `location_address`: String
- `latitude`: Decimal(9, 6)
- `longitude`: Decimal(9, 6)
- `budget`: Decimal(10, 2)
- `status`: ChoiceField (`OPEN`, `ASSIGNED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`)
- `created_at`: DateTime

### `JobRequest` / Application
- `id`: AutoField (PK)
- `job`: ForeignKey (`Job`, related_name='requests', nullable for direct hire)
- `sender`: ForeignKey (`accounts.User`, related_name='sent_requests')
- `recipient`: ForeignKey (`accounts.User`, related_name='received_requests')
- `initial_price`: Decimal(10, 2)
- `agreed_price`: Decimal(10, 2)
- `status`: ChoiceField (`PENDING`, `ACCEPTED`, `REJECTED`, `NEGOTIATING`, `COMPLETED`)
- `created_at`: DateTime

### `PriceRevisionHistory`
- `id`: AutoField (PK)
- `job_request`: ForeignKey (`JobRequest`, related_name='revisions')
- `proposed_by`: ForeignKey (`accounts.User`)
- `previous_price`: Decimal(10, 2)
- `proposed_price`: Decimal(10, 2)
- `reason`: TextField (Mandatory)
- `status`: ChoiceField (`PENDING`, `ACCEPTED`, `REJECTED`)
- `created_at`: DateTime

---

## 4. Agricultural Equipment Rental (`equipment`)

### `EquipmentItem`
- `id`: AutoField (PK)
- `owner`: ForeignKey (`accounts.User`, related_name='equipment_items')
- `name`: String (e.g., "Mahindra 575 DI Tractor", "Combine Harvester")
- `category`: ChoiceField (`TRACTOR`, `HARVESTER`, `TILLER`, `SEEDER`, `OTHER`)
- `description`: TextField
- `specifications`: JSONField (Horsepower, fuel capacity, model year)
- `hourly_rate`: Decimal(10, 2) (Nullable)
- `daily_rate`: Decimal(10, 2) (Nullable)
- `location_address`: String
- `latitude`: Decimal(9, 6)
- `longitude`: Decimal(9, 6)
- `is_available`: Boolean (Default: True)
- `image`: ImageField

### `EquipmentRentalRequest`
- `id`: AutoField (PK)
- `equipment`: ForeignKey (`EquipmentItem`, related_name='rental_requests')
- `renter`: ForeignKey (`accounts.User`, related_name='my_rentals')
- `start_date`: Date
- `end_date`: Date
- `total_price`: Decimal(10, 2)
- `status`: ChoiceField (`PENDING`, `APPROVED`, `REJECTED`, `ACTIVE`, `RETURNED`, `CANCELLED`)
- `created_at`: DateTime

---

## 5. Ratings & Reviews (`reviews`)

### `Review`
- `id`: AutoField (PK)
- `job`: OneToOneField (`jobs.Job`, related_name='review')
- `reviewer`: ForeignKey (`accounts.User`, related_name='reviews_given')
- `target_user`: ForeignKey (`accounts.User`, related_name='reviews_received')
- `rating`: Integer (1 to 5 stars)
- `comment`: TextField
- `created_at`: DateTime

---

## 6. Notifications (`notifications`)

### `Notification`
- `id`: AutoField (PK)
- `recipient`: ForeignKey (`accounts.User`, related_name='notifications')
- `title`: String
- `message`: TextField
- `notification_type`: ChoiceField (`JOB_REQUEST`, `PRICE_REVISION`, `EQUIPMENT_RENTAL`, `SYSTEM`)
- `is_read`: Boolean (Default: False)
- `created_at`: DateTime
