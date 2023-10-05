use pyo3::prelude::*;
use pyo3::types::PyBytes;

/// Formats the sum of two numbers as string.
#[pyfunction]
fn sum_as_string(a: usize, b: usize) -> PyResult<String> {
    Ok((a + b).to_string())
}

#[pyfunction]
fn nalu_decode(py: Python, data: &PyBytes) -> Py<PyAny> {
    let data = data.as_bytes();
    let mut res = Vec::with_capacity(data.len());
    let mut i = 0;
    let i_max = data.len();
    while i < i_max {
        if (i + 2 < i_max) && (data[i] == 0) && (data[i + 1] == 0) && (data[i + 2] == 3) {
            res.push(0);
            res.push(0);
            i += 3;
        } else {
            res.push(data[i]);
            i += 1;
        }
    }
    PyBytes::new(py, &res).into()
}

#[pyfunction]
fn nalu_encode(py: Python, data: &PyBytes) -> Py<PyAny> {
    let data = data.as_bytes();
    let mut res = Vec::with_capacity(data.len());
    let mut i = 0;
    let i_max = data.len();
    while i < i_max {
        if (i + 2 < i_max) && (data[i] == 0) && (data[i + 1] == 0) && (data[i + 2] < 4) {
            res.push(0);
            res.push(0);
            res.push(3);
            i += 2;
        } else {
            res.push(data[i]);
            i += 1;
        }
    }
    PyBytes::new(py, &res).into()
}

/// A Python module implemented in Rust.
#[pymodule]
fn rust_utils(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    m.add_function(wrap_pyfunction!(nalu_decode, m)?)?;
    m.add_function(wrap_pyfunction!(nalu_encode, m)?)?;
    Ok(())
}