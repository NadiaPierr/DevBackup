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

Υποστηρίζονται έτοιμοι κανόνες για Python, JavaScript/TypeScript, Java, C#, C/C++, Go, Rust, PHP και Ruby.

## Εγκατάσταση

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python .\scr\main.py
```

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

## Κατάσταση έργου

Λειτουργικό desktop prototype. Πριν από εταιρική παραγωγική χρήση προτείνονται αυτοματοποιημένα tests, CI pipeline, packaging, πολιτική retention και έλεγχος ακεραιότητας των archives.
