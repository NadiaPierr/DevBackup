# Dev Project Backup

Desktop εφαρμογή για τη δημιουργία και επαναφορά τοπικών backups έργων λογισμικού. Διαχειρίζεται πολλαπλά projects μέσα από γραφικό περιβάλλον και αποθηκεύει κάθε έκδοση ως συμπιεσμένο αρχείο ZIP.

> Το έργο βρίσκεται σε ενεργή ανάπτυξη και προορίζεται κυρίως για περιβάλλον Windows.

## Βασικές δυνατότητες

- Διαχείριση πολλών projects και ιστορικού εκδόσεων.
- Δημιουργία ονομαστικών ZIP snapshots.
- Αυτόματες εξαιρέσεις generated αρχείων ανά τεχνολογία.
- Υποστήριξη `.gitignore` και custom exclusions.
- Εξαίρεση πιθανών secrets από προεπιλογή.
- Προεπισκόπηση αρχείων και επισήμανση αρχείων άνω των 100 MB.
- Επαναφορά snapshot σε επιλεγμένο φάκελο.
- Αυτόματο safety backup πριν από επαναφορά στο ενεργό project.
- Πλήρως τοπική λειτουργία, χωρίς αποστολή δεδομένων σε τρίτους.

## Τεχνολογίες

| Περιοχή | Τεχνολογία |
| --- | --- |
| Γλώσσα | Python 3.10+ |
| Γραφικό περιβάλλον | CustomTkinter |
| Κανόνες εξαιρέσεων | pathspec |
| Διαδρομές εφαρμογής | platformdirs |
| Αποθήκευση | JSON και ZIP |
| Αυτοματοποιημένα tests | pytest |

Υποστηρίζονται έτοιμοι κανόνες για Python, JavaScript/TypeScript, Java, C#, C/C++, Go, Rust, PHP και Ruby.

## Εγκατάσταση για τελικό χρήστη

Κατέβασε το `DevProjectBackup-Setup-<version>.exe`, εκτέλεσέ το και ακολούθησε τον οδηγό εγκατάστασης. Δεν απαιτείται ξεχωριστή εγκατάσταση Python.

Ο installer δημιουργεί συντόμευση στο Start Menu και προσφέρει προαιρετική συντόμευση στην επιφάνεια εργασίας.

## Προετοιμασία για ανάπτυξη

Από PowerShell στον βασικό φάκελο του project:

```powershell
.\setup.cmd
```

Το script ελέγχει την Python, δημιουργεί το `.venv` και εγκαθιστά τις κλειδωμένες εξαρτήσεις. Για άμεση εκκίνηση σε development mode:

```powershell
.\setup.cmd -Run -Development
```

Το `.cmd` wrapper επιτρέπει την εκτέλεση χωρίς μόνιμη αλλαγή του PowerShell Execution Policy. Το αντίστοιχο PowerShell script παραμένει διαθέσιμο ως `setup.ps1`.

## Χρήση

1. Πρόσθεσε τον φάκελο ενός project.
2. Επίλεξε τεχνολογία και φάκελο αποθήκευσης.
3. Όρισε όνομα έκδοσης και δημιούργησε το backup.
4. Επίλεξε μια έκδοση από το ιστορικό όταν χρειαστεί επαναφορά.

Τα metadata αποθηκεύονται στο `%LOCALAPPDATA%\DevProjectBackup\catalogue.json`. Η προτεινόμενη τοποθεσία των ZIP είναι το `Documents\DevProjectBackups`, με δυνατότητα διαφορετικού φακέλου ανά project.

## Ασφάλεια

Η εφαρμογή εξαιρεί συνηθισμένα αρχεία credentials, παραλείπει symbolic links, αποτρέπει την αποθήκευση backup μέσα στο source project και ελέγχει τις διαδρομές των ZIP κατά την επαναφορά.

Η ανίχνευση secrets βασίζεται σε ονόματα αρχείων και δεν αντικαθιστά εξειδικευμένο security scanner. Το εργαλείο λειτουργεί συμπληρωματικά προς το version control και όχι ως πλήρης λύση disaster recovery.

## Development mode

```powershell
$env:DEV_BACKUP_ENV = "development"
python .\scr\main.py
```

Σε αυτή τη λειτουργία, τα δοκιμαστικά δεδομένα αποθηκεύονται τοπικά στον φάκελο `.devdata`.

## Αυτοματοποιημένα tests

Μετά το `setup.cmd`, εκτέλεσε τη σουίτα από τον βασικό φάκελο του project:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Τα tests χρησιμοποιούν προσωρινούς φακέλους και δεν επηρεάζουν τα projects ή τα backups του χρήστη. Καλύπτουν τη διαχείριση του καταλόγου, τους κανόνες εξαιρέσεων, τη δημιουργία ZIP, την επαναφορά αρχείων και βασικούς ελέγχους ασφαλείας.

## Δημιουργία executable και installer

Για αυτόνομο Windows executable:

```powershell
.\build.cmd
```

Το αποτέλεσμα δημιουργείται στο `dist\DevProjectBackup.exe`. Για να δημιουργηθεί και installer απαιτείται το Inno Setup 6:

```powershell
.\build.cmd -Installer
```

Ο installer δημιουργείται στο `installer-output`. Το workflow `.github/workflows/windows-build.yml` εκτελεί tests και δημιουργεί και τα δύο artifacts χειροκίνητα ή όταν γίνει push ένα tag όπως `v1.0.3`.

### Αλλαγή έκδοσης

Η έκδοση ορίζεται μόνο στο `scr/version.py`:

```python
__version__ = "1.0.3"
```

Πριν από νέο release, αύξησε αυτή την τιμή σύμφωνα με το Semantic Versioning, εκτέλεσε τους ελέγχους και δημιούργησε τα artifacts:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\build.cmd -Installer
```

Το build ενημερώνει αυτόματα:

- τα metadata του `DevProjectBackup.exe`,
- το όνομα και την έκδοση του installer,
- την έκδοση του Python project από το `pyproject.toml`,
- και την έκδοση που εμφανίζεται στον τίτλο της εφαρμογής.

Δεν χρειάζεται χειροκίνητη αλλαγή στα αρχεία `.spec`, `.iss` ή `pyproject.toml`.

Για GitHub release, το tag πρέπει να συμφωνεί με την έκδοση, π.χ. για `__version__ = "1.0.3"` χρησιμοποίησε το tag `v1.0.3`.

## Κατάσταση έργου

Λειτουργικό desktop prototype με αυτοματοποιημένα tests, Windows packaging και CI build. Πριν από εταιρική παραγωγική χρήση προτείνονται ψηφιακή υπογραφή του installer, πολιτική retention και έλεγχος ακεραιότητας των archives.
