(function () {
    let materialsCache = null;

    async function loadMaterials() {
        if (materialsCache !== null) {
            return materialsCache;
        }

        try {
            const response = await fetch("/api/materials");
            if (!response.ok) {
                materialsCache = [];
                return materialsCache;
            }

            materialsCache = await response.json();
            return materialsCache;
        } catch (error) {
            console.warn("No se pudo cargar el catálogo de materiales", error);
            materialsCache = [];
            return materialsCache;
        }
    }

    function createMaterialSelect(materials) {
        const select = document.createElement("select");
        select.className = "material-picker";
        select.innerHTML = `<option value="">Material catálogo</option>`;

        materials.forEach((material) => {
            const option = document.createElement("option");
            option.value = material.id;

            const category = material.category ? `${material.category} · ` : "";
            const unit = material.unit ? ` / ${material.unit}` : "";
            const price = Number(material.default_price || 0).toFixed(2).replace(".", ",");

            option.textContent = `${category}${material.name} - ${price} €${unit}`;
            select.appendChild(option);
        });

        return select;
    }

    function applyMaterialToRow(row, materialId, materials) {
        if (!materialId) {
            return;
        }

        const material = materials.find((item) => String(item.id) === String(materialId));
        if (!material) {
            return;
        }

        const typeInput = row.querySelector('select[name="line_type"]');
        const descriptionInput = row.querySelector('[name="description"]');
        const quantityInput = row.querySelector('input[name="quantity"]');
        const priceInput = row.querySelector('input[name="unit_price"]');

        if (typeInput) {
            typeInput.value = "material";
        }

        if (descriptionInput) {
            descriptionInput.value = material.name;
        }

        if (quantityInput && (!quantityInput.value || Number(quantityInput.value) === 0)) {
            quantityInput.value = "1";
        }

        if (priceInput) {
            priceInput.value = Number(material.default_price || 0).toFixed(2);
        }
    }

    function enhanceHeader() {
        document.querySelectorAll(".line-header").forEach((header) => {
            if (header.querySelector(".material-header")) {
                return;
            }

            const span = document.createElement("span");
            span.className = "material-header";
            span.textContent = "Material catálogo";
            header.insertBefore(span, header.firstChild);
        });
    }

    function enhanceRow(row, materials) {
        if (row.querySelector(".material-picker")) {
            return;
        }

        const lineTypeSelect = row.querySelector('select[name="line_type"]');
        if (!lineTypeSelect) {
            return;
        }

        const materialSelect = createMaterialSelect(materials);

        materialSelect.addEventListener("change", function () {
            applyMaterialToRow(row, this.value, materials);
        });

        row.insertBefore(materialSelect, lineTypeSelect);
    }

    async function enhanceAllRows() {
        const materials = await loadMaterials();

        if (!materials.length) {
            return;
        }

        enhanceHeader();

        document.querySelectorAll(".line-row").forEach((row) => {
            enhanceRow(row, materials);
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        enhanceAllRows();

        const originalAddLine = window.addLine;

        if (typeof originalAddLine === "function") {
            window.addLine = function () {
                originalAddLine();
                setTimeout(enhanceAllRows, 50);
            };
        }

        const observer = new MutationObserver(function () {
            enhanceAllRows();
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
        });
    });
})();
